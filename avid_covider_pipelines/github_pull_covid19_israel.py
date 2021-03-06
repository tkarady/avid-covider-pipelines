from dataflows import Flow, update_resource, printer
from avid_covider_pipelines.utils import dump_to_path
import os
import logging
from avid_covider_pipelines import utils
import subprocess


def flow(parameters, *_):
    logging.info('Pulling latest code from COVID19-ISRAEL github repo')
    logging.info('COVID19_ISRAEL_REPOSITORY=%s' % os.environ.get('COVID19_ISRAEL_REPOSITORY'))
    logging.info('COVID19_ISRAEL_BRANCH=%s' % os.environ.get('COVID19_ISRAEL_BRANCH'))
    if not os.environ.get('COVID19_ISRAEL_REPOSITORY'):
        logging.info('skipping pull because COVID19_ISRAEL_REPOSITORY env var is empty')
        logging.info('using env var COVID19_ISRAEL_SHA1 for the sha1')
        logging.info('COVID19_ISRAEL_SHA1=' + os.environ.get('COVID19_ISRAEL_SHA1', "_"))
        sha1 = os.environ.get('COVID19_ISRAEL_SHA1', "_")
    else:
        utils.subprocess_call_log(['git', 'config', 'user.email', 'avid-covider-pipelines@localhost'], cwd='../COVID19-ISRAEL')
        utils.subprocess_call_log(['git', 'config', 'user.name', 'avid-covider-pipelines'], cwd='../COVID19-ISRAEL')
        branch = os.environ.get('COVID19_ISRAEL_BRANCH')
        if branch:
            logging.info('Pulling from origin/' + branch)
            if utils.subprocess_call_log(['git', 'fetch', 'origin'], cwd='../COVID19-ISRAEL') != 0:
                raise Exception('Failed to fetch origin')
            if utils.subprocess_call_log(['git', 'checkout', branch], cwd='../COVID19-ISRAEL') != 0:
                raise Exception('Failed to switch branch')
            if utils.subprocess_call_log(['git', 'pull', 'origin', branch], cwd='../COVID19-ISRAEL') != 0:
                raise Exception('Failed to git pull')
        else:
            logging.info('pulling from origin/master')
            if utils.subprocess_call_log(['git', 'pull', 'origin', 'master'], cwd='../COVID19-ISRAEL') != 0:
                raise Exception('Failed to git pull')
        sha1 = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd='../COVID19-ISRAEL').decode().strip()
    # sha1 = subprocess.check_output(['cat', '/pipelines/data/fake-sha1'], cwd='../COVID19-ISRAEL').decode().strip()
    if parameters.get('change-run-covid'):
        with open('avid_covider_pipelines/run_covid19_israel.py', 'r') as f:
            lines = f.readlines()
        with open('avid_covider_pipelines/run_covid19_israel.py', 'w') as f:
            for i, line in enumerate(lines):
                if i == 0:
                    if line.startswith('COVID19_ISRAEL_GITHUB_SHA1 = '):
                        line = 'COVID19_ISRAEL_GITHUB_SHA1 = "%s"\n' % sha1
                    else:
                        f.write('COVID19_ISRAEL_GITHUB_SHA1 = "%s"\n' % sha1)
                f.write(line)
    return Flow(
        iter([{'sha1': sha1}]),
        update_resource(-1, name='github_pull_covid19_israel', path='github_pull_covid19_israel.csv', **{'dpp:streaming': True}),
        printer(),
        dump_to_path(parameters.get('dump_to_path', 'data/github_pull_covid19_israel'))
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    flow({}).process()
