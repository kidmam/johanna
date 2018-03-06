#!/usr/bin/env python3
import json

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()


def run_create_cloudwatch_dashboard(name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    print_message('get elasticbeanstalk environment info: %s' % name)

    cmd = ['elasticbeanstalk', 'describe-environments']
    result = aws_cli.run(cmd)

    env_list = list()
    for ee in result['Environments']:
        ename = ee['EnvironmentName']
        if ename.startswith(name):
            env_list.append(ee)

    env_instances_list = list()

    for ee in env_list:
        cmd = ['elasticbeanstalk', 'describe-environment-resources']
        cmd += ['--environment-id', ee['EnvironmentId']]
        result = aws_cli.run(cmd)
        ee_res = result['EnvironmentResources']
        for instance in ee_res['Instances']:
            ii = dict()
            ii['Id'] = instance['Id']
            ii['EnvironmentName'] = ee_res['EnvironmentName']
            env_instances_list.append(ii)

    ################################################################################

    print_message('create or update cloudwatch dashboard: %s' % name)

    template_name = env['template']['NAME']
    region = settings['AWS_DEFAULT_REGION']
    filename_path = 'template/%s/cloudwatch/%s_%s.json' % (template_name, name, region)
    with open(filename_path, 'r') as ff:
        dashboard_body = json.load(ff)

    for dw in dashboard_body['widgets']:
        pm = dw['properties']['metrics']

        env_name_only = True
        for dimension in pm[0]:
            if dimension == 'InstanceId':
                env_name_only = False

        template = json.dumps(pm[0])
        new_metrics_list = list()
        if env_name_only:
            for ii in env_list:
                new_metric = template.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
                new_metric = json.loads(new_metric)
                new_metrics_list.append(new_metric)
        else:
            for ii in env_instances_list:
                new_metric = template.replace('INSTANCE_ID', ii['Id'])
                new_metric = new_metric.replace('ENVIRONMENT_NAME', ii['EnvironmentName'])
                new_metric = json.loads(new_metric)
                new_metrics_list.append(new_metric)

        dw['properties']['metrics'] = new_metrics_list

    dashboard_body = json.dumps(dashboard_body)

    cmd = ['cloudwatch', 'put-dashboard']
    cmd += ['--dashboard-name', name]
    cmd += ['--dashboard-body', dashboard_body]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('create cloudwatch dashboard')

cw = env['cloudwatch']
cw_dashboards = cw['DASHBOARDS']
for cd in cw_dashboards:
    run_create_cloudwatch_dashboard(cd['NAME'], cd)
