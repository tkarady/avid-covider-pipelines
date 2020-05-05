import os
from dataflows import Flow
import tempfile
from corona_data_collector import add_gps_coordinates, export_corona_bot_answers, load_from_db, download_gdrive_data
import logging
import random
import subprocess
from avid_covider_pipelines import utils


DOMAIN = os.environ["AVIDCOVIDER_PIPELINES_DATA_DOMAIN"]
AUTH_USER, AUTH_PASSWORD = os.environ["AVIDCOVIDER_PIPELINES_AUTH"].split(" ")


def _mock_gender_other(rows):
    if rows.res.name == "db_data":
        logging.info("Mocking sex 'other' for ids 640000 to 640100")
        for row in rows:
            if 640000 <= int(row["__id"]) <= 640100:
                row["sex"] = '"other"'
            yield row
    else:
        for row in rows:
            yield row


def main():
    with tempfile.TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, ".netrc"), "w") as f:
            f.write("machine %s\nlogin %s\npassword %s\n" % (DOMAIN, AUTH_USER, AUTH_PASSWORD))
        HOME = os.environ["HOME"]
        os.environ["HOME"] = tempdir
        os.makedirs("data/corona_data_collector/gps_data_cache", exist_ok=True)
        utils.http_stream_download("data/corona_data_collector/gps_data_cache/datapackage.json", {
            "url": "https://%s/data/corona_data_collector/gps_data_cache/datapackage.json" % DOMAIN})
        utils.http_stream_download("data/corona_data_collector/gps_data_cache/gps_data.csv", {
            "url": "https://%s/data/corona_data_collector/gps_data_cache/gps_data.csv" % DOMAIN})
        Flow(
            download_gdrive_data.flow({
                "limit_rows": 50000,
                "files_dump_to_path": "data/corona_data_collector/gdrive_data",
                "google_drive_csv_folder_id": "1pzAyk-uXy__bt1tCX4rpTiPZNmrehTOz",
                "file_sources": {
                    "COVID-19-English.csv": "google",
                    "COVID-19-Russian.csv": "google",
                    "COVID-19-Hebrew.csv": "hebrew_google",
                    "maccabi_updated.csv": "maccabi",
                }
            }),
            load_from_db.flow({
                "where": "(id > 500 and id < 1000) or (id > 180000 and id < 185000) or (id > 600000 and id < 601000) or (id > 640000 and id < 641000) or (id > 670000)"
            }),
            _mock_gender_other,
            add_gps_coordinates.flow({
                "source_fields": {
                    "db": {
                        "street": "street",
                        "city_town": "city",
                    },
                    "google": {
                        "Street": "street",
                        "Город проживания": "street",
                        "City": "city",
                        "Улица": "city",
                    },
                    "hebrew_google": {
                        "עיר / ישוב מגורים": "city",
                        "עיר / יישוב מגורים": "city",
                        "רחוב מגורים": "street",
                    },
                    "maccabi": {
                        "yishuv": "city",
                    }
                },
                "dump_to_path": "data/corona_data_collector/with_gps_data",
                "gps_datapackage_path": "data/corona_data_collector/gps_data_cache",
                "get-coords-callback": lambda street, city: (random.uniform(29, 34), random.uniform(34, 36), int(street != city))
            }),
            export_corona_bot_answers.flow({
                "destination_output": "data/corona_data_collector/corona_bot_answers"
            }),
            export_corona_bot_answers.flow({
                "unsupported": True,
                "destination_output": "data/corona_data_collector/corona_bot_answers_unsupported"
            })
        ).process()
    os.environ["HOME"] = HOME
    subprocess.check_call(["python3", "-m", "src.utils.get_raw_data"], cwd="../COVID19-ISRAEL", env={
        **os.environ,
        "GOOGLE_SERVICE_ACCOUNT_FILE": os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"],
        "AVIDCOVIDER_LOCAL_PATH": os.getcwd()
    })
    subprocess.check_call(["python3", "-m", "src.utils.preprocess_raw_data"], cwd="../COVID19-ISRAEL", env={
        **os.environ
    })
    logging.info("Great Success!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
