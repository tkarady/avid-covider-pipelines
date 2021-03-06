from ruamel import yaml
from avid_covider_pipelines import run_covid19_israel
import logging
import os
import requests
import csv
import codecs


def predownload_data():
    if os.environ.get("AVIDCOVIDER_PIPELINES_USER") and os.environ.get("AVIDCOVIDER_PIPELINES_PASSWORD") and os.environ.get("AVIDCOVIDER_PIPELINES_URL"):
        logging.info("predownloading from avidcovider pipelines data")
        with requests.get(
            os.environ["AVIDCOVIDER_PIPELINES_URL"] + "/data/covid19_israel_files_list/files_list.csv",
            auth=(os.environ["AVIDCOVIDER_PIPELINES_USER"], os.environ["AVIDCOVIDER_PIPELINES_PASSWORD"]),
            stream=True,
        ) as res:
            dict_reader = csv.DictReader(codecs.iterdecode(res.iter_lines(), 'utf-8'), delimiter=',')
            for row in dict_reader:
                if row['size'] and int(row['size']) > 0:
                    filename = os.path.join("..", "COVID19-ISRAEL", row['name'])
                    if not os.path.exists(filename):
                        logging.info("Downloading file " + filename)
                        os.makedirs(os.path.dirname(filename), exist_ok=True)
                        with requests.get(
                            url=os.environ["AVIDCOVIDER_PIPELINES_URL"] + "/COVID19-ISRAEL/" + row['name'],
                            auth=(os.environ["AVIDCOVIDER_PIPELINES_USER"], os.environ["AVIDCOVIDER_PIPELINES_PASSWORD"]),
                            stream=True,
                        ) as fileres:
                            fileres.raise_for_status()
                            with open(filename, 'wb') as f:
                                for chunk in fileres.iter_content(chunk_size=8192):
                                    if chunk:  # filter out keep-alive new chunks
                                        f.write(chunk)
    else:
        logging.info("missing AVIDCOVIDER env vars - not predownloading")


def run_pipeline(source_spec, id):
    logging.info('running pipeline "%s"' % id)
    pipeline = source_spec[id]
    run_covid19_israel.flow({
        **{
            "output-dir": "data/%s" % id,
        },
        **pipeline
    }).process()
    dependants = pipeline.get('__dependants', [])
    logging.info('pipeline "%s" completed, running dependants: %s' % (id, dependants))
    for dependant in dependants:
        run_pipeline(source_spec, dependant)
    logging.info('completed all dependants for pipeline "%s"' % id)


def main():
    predownload_data()
    with open("covid19israel.source-spec.yaml") as f:
        source_spec = yaml.safe_load(f)
    start_ids = set()
    for id, pipeline in source_spec.items():
        num_dependencies = 0
        for dependency in pipeline.get('dependencies', []):
            if dependency in ['corona_data_collector', 'github_pull_covid19_israel']: continue
            num_dependencies += 1
            source_spec[dependency].setdefault('__dependants', set()).add(id)
        if num_dependencies == 0:
            start_ids.add(id)
    for id in start_ids:
        run_pipeline(source_spec, id)
    logging.info('all pipelines completed')


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
