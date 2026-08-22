from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth import get_user_model
from .forms import UserCreationCustomForm, UserEditCustomForm, UserLoginForm

User = get_user_model()

class ERPLoginView(LoginView):
    form_class = UserLoginForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('patients:list')


class ERPLogoutView(LogoutView):
    next_page = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "You have been logged out successfully.")
        return super().dispatch(request, *args, **kwargs)


class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'system_users'
    paginate_by = 20

    def get_queryset(self):
        return User.objects.order_by('-id')


class UserCreateView(LoginRequiredMixin, CreateView):
    model = User
    form_class = UserCreationCustomForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:list')

    def form_valid(self, form):
        try:
            user = form.save()
            messages.success(self.request, f"User account '{user.username}' ({user.get_role_display()}) created successfully!")
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f"Error creating user: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors in the form below.")
        return super().form_invalid(form)


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserEditCustomForm
    template_name = 'users/user_edit_form.html'
    success_url = reverse_lazy('users:list')

    def form_valid(self, form):
        try:
            user = form.save()
            messages.success(self.request, f"User account '{user.username}' updated successfully!")
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f"Error updating user: {str(e)}")
            return self.form_invalid(form)


class UserDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    success_url = reverse_lazy('users:list')

    def post(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            messages.error(request, "You cannot delete your own active session user account.")
            return redirect(self.success_url)
        messages.success(request, f"User account '{user.username}' deleted successfully.")
        return super().post(request, *args, **kwargs)
