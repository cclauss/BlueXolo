import json
import paramiko

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView
from pexpect import pxssh
from random import choice
from scp import SCPClient
from string import ascii_lowercase, digits

from apps.Products.models import Source
from apps.Testings.models import Keyword, TestCase
from .forms import ServerProfileForm, ServerTemplateForm, ParametersForm
from .models import TemplateServer, ServerProfile, Parameters

from celery import shared_task


class ServerTemplateView(LoginRequiredMixin, TemplateView):
    template_name = "servers-templates.html"


class NewServerTemplate(LoginRequiredMixin, CreateView):
    template_name = "create-server-template.html"
    model = TemplateServer
    success_url = reverse_lazy('servers-templates')
    form_class = ServerTemplateForm

    def get_context_data(self, **kwargs):
        context = super(NewServerTemplate, self).get_context_data(**kwargs)
        context['ParametersForm'] = ParametersForm
        return context


class EditServerTemplate(LoginRequiredMixin, UpdateView):
    model = TemplateServer
    template_name = "edit-server-template.html"
    success_url = reverse_lazy('servers-templates')
    form_class = ServerTemplateForm

    def get_context_data(self, **kwargs):
        context = super(EditServerTemplate, self).get_context_data(**kwargs)
        context['ParametersForm'] = ParametersForm
        return context


class DeleteServerTemplate(LoginRequiredMixin, DeleteView):
    model = TemplateServer
    template_name = "delete-template.html"

    def get_success_url(self):
        messages.success(self.request, "Template Deleted")
        return reverse_lazy('servers-templates')


class ServerProfileView(LoginRequiredMixin, TemplateView):
    template_name = "server-profiles.html"


class NewServerProfileView(LoginRequiredMixin, CreateView):
    template_name = "create-server-profile.html"
    success_url = reverse_lazy('servers-profiles')
    form_class = ServerProfileForm


class EditServerProfileView(LoginRequiredMixin, UpdateView):
    template_name = "edit-server-profile.html"
    success_url = reverse_lazy('servers-profiles')
    form_class = ServerProfileForm
    model = ServerProfile


class DeleteServerProfile(LoginRequiredMixin, DeleteView):
    model = ServerProfile
    template_name = "delete-profile.html"

    def get_success_url(self):
        messages.success(self.request, "Profile Deleted")
        return reverse_lazy('servers-profiles')


class ParametersView(LoginRequiredMixin, TemplateView):
    template_name = "parameters.html"


class NewParametersView(LoginRequiredMixin, CreateView):
    template_name = 'create-edit-parameter.html'
    success_url = reverse_lazy('parameters')
    form_class = ParametersForm

    def get_success_url(self):
        messages.success(self.request, "Parameter Created")
        return reverse_lazy('parameters')

    def get_context_data(self, **kwargs):
        context = super(NewParametersView, self).get_context_data(**kwargs)
        context['title'] = 'Create Parameter'
        return context


class EditParametersView(LoginRequiredMixin, UpdateView):
    template_name = "create-edit-parameter.html"
    success_url = reverse_lazy("parameters")
    form_class = ParametersForm
    model = Parameters

    def get_success_url(self):
        messages.success(self.request, "Parameter Edited")
        return reverse_lazy('parameters')

    def get_context_data(self, **kwargs):
        context = super(EditParametersView, self).get_context_data(**kwargs)
        context['title'] = 'Edit Parameter'
        return context


class DeleteParametersView(LoginRequiredMixin, DeleteView):
    model = Parameters
    template_name = "delete-parameters.html"

    def get_success_url(self):
        messages.success(self.request, "Parameter Deleted")
        return reverse_lazy('parameters')


# - - - - - - - - - Run on Server functions - - - - - - - - - - -

def get_config_object(params):
    """get config object for connection"""
    data_result = dict()
    for var in params:
        try:
            param = Parameters.objects.get(pk=var.get('id'))
            data_result['{0}'.format(param.name)] = var.get('value')
        except Exception as error:
            data_result['text'] = '{0}'.format(error)
    return data_result


def get_connection(config):
    """Create a paramiko connection for ssh communication"""
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    _port = int(config.get('port')) or 22
    client.connect(config.get('host'), username=config.get('user'), password=config.get('passwd'), port=_port)
    return client


def generate_filename(_script):
    """Generate a string like NAME_w0ln0t3j39wm"""
    name = _script.replace(" ", "")
    random_string = ''.join(choice(ascii_lowercase + digits) for i in range(12))
    return '{0}_{1}'.format(name, random_string)


def check_dirs_destiny(path, client, attempt=None):
    """First need to know if the dirs schema exist"""
    exist = True
    _attempt = attempt or 0
    try:
        _, stdout, _ = client.exec_command(
            "if test -d '{0}'; then echo '1'; else  echo '0'; fi".format(path))
        pre_res = stdout.read()
        res = pre_res.decode('ascii').replace("\n", "")
        if res == '0' and _attempt < 1:
            stdin, stdout, stderr = client.exec_command("mkdir {0}".format(path))
            _attemp += 1
            exist = check_dirs_destiny(path, client, _attemp)
        else:
            raise Exception()
    except Exception as error:
        exist = False
    return exist


def send_files(filename, file_type, config, client):
    """sent files Via SSH"""
    _data = dict()
    try:
        path = config.get('path')
        dirs = ['Keywords', 'Libraries', 'Profiles', 'Resources', 'Templates', 'TestScripts', 'Tools', 'TestSuites',
                'Results']
        for directory in dirs:
            res = check_dirs_destiny("{0}/{1}".format(path, directory), client)
            if not res:
                raise Exception("Destination directory does not exist, you don't have write permission.")
        """SCPCLient takes a paramiko transport as its only argument"""
        scp = SCPClient(client.get_transport())
        scp.put(filename, remote_path='{0}/{1}'.format(path, dirs[file_type]))
        scp.close()
    except Exception as error:
        _data['text'] = error
    return _data


def run_script(filename, config):
    """This execute pybot with some flags """
    _data = dict()
    try:
        ssh = pxssh.pxssh()
        ssh.login(config.get('host'), config.get('user'), config.get('passwd'))
        ssh.sendline("cd {0}/Results".format(config.get('path')))
        ssh.sendline("pybot -V ../Profiles/{0}_profile.py"
                     " -o {0}_output.xml"
                     " -l {0}_log.html"
                     " -r {0}_report.html"
                     " ../TestScripts/{0}_test_case.robot".format(filename))
        ssh.prompt()
        _data['text'] = ssh.before
        ssh.logout()
    except pxssh.ExceptionPxssh as error:
        print(error)
    return _data


def get_libraries():
    libraries = Source.objects.filter(
        Q(category=5) &
        Q(depends__category=4)
    )
    return libraries


def generate_profile(params, filename):
    arguments = params.get('global_variables')
    var_file = open("{0}/profiles/{1}_profile.py".format(settings.MEDIA_ROOT, filename), "w")
    for arg in arguments:
        param = Parameters.objects.get(pk=arg.get('id'))
        var_file.write("{0} = {1}".format(param.name, arg.get('value')))
        var_file.write("\n")
    var_file.close()
    return var_file.name


def generate_file(obj, type_script, params, filename, client):
    _data = ''
    try:
        config = params.get('config')
        libraries = get_libraries()
        """Generate robot files"""
        if type_script is 1:
            """First create the keyword file"""
            kwd_file = open("{0}/test_keywords/{1}_keyword.robot".format(settings.MEDIA_ROOT, filename), "w")
            kwd_file.write("*** Keywords ***")
            kwd_file.write("\n")
            kwd_file.write(obj.name)
            kwd_file.write("\n")
            kwd_file.write("\t")
            full_script = obj.script.splitlines(True)
            for line in full_script:
                kwd_file.write("\t{0}".format(line))
            kwd_file.close()

            """need to know if the dirs schema exist and then send the files"""
            _data = send_files(kwd_file.name, 0, config, client)
            if _data['text']:
                raise Exception(_data['text'])

            """Then Test Case file"""
            dummy_tc_file = open("{0}/test_keywords/{1}_test_case.robot".format(settings.MEDIA_ROOT, filename), "w")
            dummy_tc_file.write("*** Settings ***\n")
            dummy_tc_file.write("Resource\t{0}/Keywords/{1}_keyword.robot\n".format(config.get('path'), filename))
            """Now add the libraries """
            if libraries:
                for lib in libraries:
                    dummy_tc_file.write("Library\t{0}\n".format(lib.name))
                dummy_tc_file.write("\n")
            dummy_tc_file.write("*** Test Cases ***")
            dummy_tc_file.write("\n")
            dummy_tc_file.write('Test {}'.format(obj.name.replace(" ", "")))
            dummy_tc_file.write("\n")
            dummy_tc_file.write("\t")
            dummy_tc_file.write("[Tags]  TestKeyword")
            dummy_tc_file.write("\n")
            dummy_tc_file.write("\t")
            dummy_tc_file.write(obj.name)
            dummy_tc_file.close()

            send_files(dummy_tc_file.name, 5, config, client)

        elif type_script is 2:
            """Test Case"""
            tc_file = open("{0}/test_cases/{1}_test_case.robot".format(settings.MEDIA_ROOT, filename), "w")
            tc_file.write("*** Settings ***\n")
            """Now add the libraries """
            if libraries:
                for lib in libraries:
                    tc_file.write("Library\t{0}\n".format(lib.name))
                tc_file.write("\n")
            tc_file.write("*** Test Cases ***")
            tc_file.write("\n")
            tc_file.write(obj.name)
            tc_file.write("\n")
            tc_file.write("\t")
            tc_file.write("[Tags]\t\t{0}".format(obj.phase.name))
            tc_file.write("\n")
            tc_file.write("\t")
            full_script = obj.script.splitlines(True)
            for line in full_script:
                tc_file.write("\t{0}".format(line))
            tc_file.close()
            send_files(tc_file.name, 5, config, client)

        """Need a variables Profile File"""
        profile = generate_profile(params, filename)
        send_files(profile, 2, config, client)
        _data = 'Created'
    except Exception as error:
        _data['error'] = error
    return _data


def get_result_files(client, filename, config):
    """Obtain the Results files (html and xml) for show it"""
    _data = dict()
    try:
        scp = SCPClient(client.get_transport())
        scp.get('{0}/Results/{1}_log.html'.format(config.get('path'), filename),
                '{0}/test_result/'.format(settings.MEDIA_ROOT))
        scp.get('{0}/Results/{1}_output.xml'.format(config.get('path'), filename),
                '{0}/test_result/'.format(settings.MEDIA_ROOT))
        scp.get('{0}/Results/{1}_report.html'.format(config.get('path'), filename),
                '{0}/test_result/'.format(settings.MEDIA_ROOT))
        scp.close()
        client.close()
        _data['text'] = 'Success'
    except Exception as error:
        _data['text'] = error
    return _data


@shared_task()
def run_on_server(_data):
    """The main function to send scripts """
    type_script = _data.get('type_script')
    data_result = dict()
    params = dict()
    profile_category = 0
    try:
        profiles = ServerProfile.objects.filter(pk__in=_data.get('profiles'))
        for profile in profiles:
            if profile.category == 1:
                """is global variables"""
                params['global_variables'] = json.loads(profile.config)
            elif profile.category in [2, 3]:
                profile_category = profile.category
                """is local connection or jenkins"""
                params['config'] = get_config_object(json.loads(profile.config))
        configs = params.get('config')
        filename = _data.get('filename')
        client = get_connection(configs)
        if type_script is 1:
            """is keywords"""
            obj = Keyword.objects.get(id=_data.get('obj_id'))
            """Execute the kwd"""
        elif type_script is 2:
            obj = TestCase.objects.get(id=_data.get('obj_id'))
        _data = generate_file(obj, type_script, params, filename, client)
        if _data['error']:
            raise Exception(_data['error'])
        if profile_category is 2:
            """Run pybot only if the user choose -> Local Network connection"""
            run_script(filename, configs)
            get_result_files(client, filename, configs)
            data_result['link'] = "{0}/{1}test_result/{2}_report.html".format(settings.SITE_DNS,
                                                                              settings.MEDIA_URL,
                                                                              filename)
        else:
            data_result['text'] = 'Success'
    except Exception as error:
        data_result['error'] = '{0}'.format(error)
    return data_result
