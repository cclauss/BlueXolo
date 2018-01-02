from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, DeleteView, CreateView, UpdateView, DetailView
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from apps.Testings.models import Keyword, Collection, TestCase, TestSuite
from apps.Testings.forms import CollectionForm, ImportScriptForm, EditImportScriptForm


class KeyWordsView(LoginRequiredMixin, TemplateView):
    template_name = "keywords.html"
    # required_permission = "read_keyword"


class NewKeywordView(LoginRequiredMixin, TemplateView):
    template_name = "create-keyword.html"
    # required_permission = "create_keyword"


class EditKeywordView(LoginRequiredMixin, DetailView):
    model = Keyword
    template_name = "edit-keyword.html"
    # required_permission = "update_keyword"


class DeleteKeywordView(LoginRequiredMixin, DeleteView):
    template_name = "delete-keyword.html"
    model = Keyword

    # required_permission = "delete_keyword"

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.user == request.user or request.user.is_staff:
            return super(DeleteKeywordView, self).dispatch(request, *args, **kwargs)
        elif obj.user != request.user:
            messages.warning(request, "You don't have permission for this action")
            return redirect('keywords')

    def get_success_url(self):
        messages.success(self.request, "Keyword Deleted")
        return reverse_lazy('keywords')


class TestCaseView(LoginRequiredMixin, TemplateView):
    template_name = "testcases.html"
    # required_permission = "read_test_case"


class NewTestCaseView(LoginRequiredMixin, TemplateView):
    template_name = "create-testcase.html"
    # required_permission = "create_test_case"


class EditTestCaseView(LoginRequiredMixin, DetailView):
    model = TestCase
    template_name = "edit-testcase.html"
    # required_permission = "update_test_case"


class DeleteTestCaseView(LoginRequiredMixin, DeleteView):
    template_name = "delete-testcase.html"
    model = TestCase

    # required_permission = "delete_test_case"

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.user == request.user or request.user.is_staff:
            return super(DeleteTestCaseView, self).dispatch(request, *args, **kwargs)
        elif obj.user != request.user:
            messages.warning(request, "You don't have permission for this action")
            return redirect('testcases')

    def get_success_url(self):
        messages.success(self.request, "Test Case Deleted")
        return reverse_lazy('testcases')


class TestSuiteView(LoginRequiredMixin, TemplateView):
    template_name = "testsuites.html"
    # required_permission = "read_test_suite"


class NewTestSuiteView(LoginRequiredMixin, TemplateView):
    template_name = "create-testsuites.html"
    # required_permission = "create_test_suite"


class EditTestSuiteView(LoginRequiredMixin, DetailView):
    model = TestSuite
    template_name = "edit-testsuites.html"
    # required_permission = "update_test_suite"


class DeleteTestSuiteView(LoginRequiredMixin, DeleteView):
    template_name = "delete-testsuite.html"
    model = TestSuite

    # required_permission = "delete_test_suite"

    def get_success_url(self):
        messages.success(self.request, "Test Suite Deleted")
        return reverse_lazy("testsuites")

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.user == request.user or request.user.is_staff:
            return super(DeleteTestSuiteView, self).dispatch(request, *args, **kwargs)
        elif obj.user != request.user:
            messages.warning(request, "You don't have permission for this action")
            return redirect('testsuites')


class CollectionsView(LoginRequiredMixin, TemplateView):
    template_name = "collections.html"
    # required_permission = "read_collection"


class NewCollectionsView(LoginRequiredMixin, CreateView):
    model = Collection
    form_class = CollectionForm
    template_name = "create-edit-collection.html"

    # required_permission = "create_collection"

    def get_success_url(self):
        messages.success(self.request, "Collection Created")
        return reverse_lazy('collections')

    def get_context_data(self, **kwargs):
        context = super(NewCollectionsView, self).get_context_data(**kwargs)
        context['title'] = "New Collection"
        return context


class EditCollectionsView(LoginRequiredMixin, UpdateView):
    model = Collection
    form_class = CollectionForm
    template_name = "create-edit-collection.html"

    # required_permission = "update_collection"

    def get_success_url(self):
        messages.success(self.request, "Collection Edited")
        return reverse_lazy('collections')

    def get_context_data(self, **kwargs):
        context = super(EditCollectionsView, self).get_context_data(**kwargs)
        context['title'] = "Edit Collections"
        return context


class DeleteCollectionsView(LoginRequiredMixin, DeleteView):
    model = Collection
    template_name = "delete-collections.html"

    # required_permission = "delete_collection"

    def get_success_url(self):
        messages.success(self.request, "Collection Deleted")
        return reverse_lazy('collections')

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.user == request.user or request.user.is_staff:
            return super(DeleteCollectionsView, self).dispatch(request, *args, **kwargs)
        elif obj.user != request.user:
            messages.warning(request, "You don't have permission for this action")
            return redirect('collections')


class KeywordsImportedView(LoginRequiredMixin, TemplateView):
    template_name = "list-import-script.html"
    # required_permission = "read_imported_script"


class NewKeywordImportedView(LoginRequiredMixin, CreateView):
    template_name = "import-script.html"
    form_class = ImportScriptForm
    model = Keyword

    # required_permission = "create_imported_script"

    def form_valid(self, form):
        file = form.files.get('file_script')
        if file:
            try:
                file_content = file.read()
                form.instance.script = file_content
                form.instance.user = self.request.user
                form.instance.script_type = 2
                form.save()
            except Exception as error:
                print(error)
        messages.success(self.request, "Script imported")
        return super(NewKeywordImportedView, self).form_valid(form)

    def form_invalid(self, form):
        return super(NewKeywordImportedView, self).form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('edit-import-script', kwargs={'pk': self.object.pk})


class EditKeywordImportedView(LoginRequiredMixin, UpdateView):
    form_class = EditImportScriptForm
    template_name = "edit-import-script.html"
    model = Keyword

    # required_permission = "update_imported_script"

    def form_valid(self, form):
        messages.success(self.request, "Script updated")
        return super(EditKeywordImportedView, self).form_valid(form)

    def form_invalid(self, form):
        return super(EditKeywordImportedView, self).form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('edit-import-script', kwargs={'pk': self.object.pk})


class DeleteImportedScriptView(LoginRequiredMixin, DeleteView):
    model = Keyword
    template_name = 'delete-imported-script.html'

    # required_permission = "delete_imported_script"

    def get_success_url(self):
        messages.success(self.request, "Script deleted")
        return reverse_lazy('imported-scripts')

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.user == request.user or request.user.is_staff:
            return super(DeleteImportedScriptView, self).dispatch(request, *args, **kwargs)
        elif obj.user != request.user:
            messages.warning(request, "You don't have permission for this action")
            return redirect('imported-scripts')


def apply_highlight(script):
    """This function use a pygments library for make a html highlight element. """
    if script:
        try:
            lexer = get_lexer_by_name("robotframework", stripall=True)
            formatter = HtmlFormatter(linenos=False, cssclass="source")
            with_highlight = highlight(script, lexer, formatter)
            return with_highlight
        except Exception as error:
            print(error)


class RunScriptView(LoginRequiredMixin, TemplateView):
    template_name = "run_script.html"

    # required_permission = "run_scripts"

    def get_context_data(self, **kwargs):
        context = super(RunScriptView, self).get_context_data(**kwargs)
        type_script = int(kwargs.get('type_script'))
        scripts = ['Keyword', 'Test Case', 'Test Suite']
        if type_script:
            if type_script is 1:
                obj = Keyword.objects.get(pk=kwargs.get('pk'))
            if type_script is 2:
                obj = TestCase.objects.get(pk=kwargs.get('pk'))
            if type_script is 3:
                obj = TestSuite.objects.get(pk=kwargs.get('pk'))
            context['obj'] = obj
            context['type'] = scripts[type_script - 1]
            context['type_id'] = type_script
            context['script'] = apply_highlight(obj.script)
        return context
