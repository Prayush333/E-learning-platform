from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView 
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin
)
from .models import Course
from django.shortcuts import get_object_or_404, redirect
from django.views.generic.base import TemplateResponseMixin, View
from .form import ModuleFormSet
from django.apps import apps
from django.forms.models import modelform_factory
from .models import Module, Content


class OwnerMixin:

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owner=self.request.user)


class OwnerEditMixin:

    def from_valid(self, form):
        from.instance.owner = self.request.user 
        return super().form_valid(form)
    

class OwnerCourseMixin(
    OwnerMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin
    ):
    model = Course
    fields = ['subject', 'title', 'slug', 'overview']
    success_url = reverse_lazy('manage_course_list') 


class OwnerCourseEditMixin(OwnerCourseMixin, OwnerCourseEditMixin):
    template_name= 'courses/manage/course/form.html'
    

class ManageCourseListView(OwnerCourseMixin, ListView):
    template_name = 'courses/manage/course/list.html'
    permission_required='courses.view_course'


class CourseCreateView(OwnerCourseEditMixin, CreateView):
    permission_required='courses.add_course'
    

class CourseUpdateView(OwnerCourseEditMixin, UpdateView):
    permission_required='courses.change_course'


class CourseDeleteView(OwnerCourseMixin, DeleteView):
    template_name = 'courses/manage/course/delete.html'
    permission_required='courses.delete_course'


class CourseModuleUpdateView(TemplateResponseMixin, View):
    template_name = 'courses/manage/module/formset.html'
    Course=None

    def get_formset(self, data=None):
        return ModuleFormSet(instance=self.Course, data=data)
    
    def dispatch(self, request, pk):
        self.course = get_object_or_404(Course, id=pk, owner=request.user)
        return super().dispatch(request, pk)
    
    def get(self, request, *args, **kwargs):
        formset = self.get_formset()
        return self.render_to_response(
            {
                'course':self.course,
                'formset':formset
            }
        )
    
    def post(self, request, *args,**kwargs):
        formset= self.get_formset(data=request.POST)
        if formset.is_valid():
            formset.save()
            return redirect('manage_course_list')
        return self.render_to_response(
            {
                'course': self.course,
                'formset': formset
            }
        )

class ContentCreateUpdateView(TemplateResponseMixin, View):
    module = None
    model = None
    obj = None
    template_name = 'courses/manage/content/form.html'

    def get_model(self, model_name):
        if model_name in ['text', 'video', 'image', 'file']:
            return apps.get_model(
            app_label='courses', model_name=model_name
            )
        return None
    
    def get_form(self, model, *args, **kwargs):
        Form = modelform_factory(
        model,
        exclude=['owner', 'order', 'created', 'updated']
        )
        return Form(*args, **kwargs)

    def dispatch(self, request, module_id, model_name, id=None):
        self.module = get_object_or_404(
        Module, id=module_id, course__owner=request.user
        )
        self.model = self.get_model(model_name)

        if id:
            self.obj=get_object_or_404(
                self.model, 
                id=id,
                owner=request.user
                )
            return super().dispatch(request, module_id, model_name, id)
    
    def get(self, request, module_id, model_name, id=None):
        form = self.get_form(self.model, instance=self.obj)
        return self.render_to_response(
        {'form': form, 'object': self.obj}
        )
    
    def post(self, request, module_id, model_name, id=None):
        form = self.get_form(
        self.model,
        instance=self.obj,
        data=request.POST,
        files=request.FILES
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()

            if not id:
                Content.objects.create(module=self.module, item=obj)
                
            return redirect('module_content_list', self.module.id)
            
        return self.render_to_response(
        {'form': form, 'object': self.obj}
        )
    