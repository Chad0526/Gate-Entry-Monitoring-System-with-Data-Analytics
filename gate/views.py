from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
    View,
)
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect

from gate_analytics.roles import RoleRequiredMixin, role_required
from .models import (
    EventCategory,
    Event,
    JobCategory,
    EventJobCategoryLinking,
    EventMember,
    EventUserWishList,
    UserCoin,
    EventImage,
    EventAgenda

)
from .forms import EventForm, EventImageForm, EventAgendaForm, EventAgendaFormSet, EventCreateMultiForm, EventStatusForm


# Events: admin, faculty, staff only (no guard)
EVENT_ROLES = ['admin', 'faculty', 'staff']


def _ensure_default_event_categories(user):
    if EventCategory.objects.exists():
        return
    defaults = [
        ('Seminar', 'SEMIN', 1),
        ('Workshop', 'WORK', 2),
        ('Sports Fest', 'SPORT', 3),
        ('Cultural Night', 'CULT', 4),
        ('Orientation', 'ORIEN', 5),
        ('Webinar', 'WEB', 6),
        ('Competition', 'COMP', 7),
        ('Community Outreach', 'OUT', 8),
    ]
    for name, code, priority in defaults:
        EventCategory.objects.create(
            name=name,
            code=code,
            priority=priority,
            created_user=user,
            updated_user=user,
            status='active',
        )

# Event category list view
class EventCategoryListView(RoleRequiredMixin, LoginRequiredMixin, ListView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = EventCategory
    template_name = 'events/event_category.html'
    context_object_name = 'event_category'


class EventCategoryCreateView(RoleRequiredMixin, LoginRequiredMixin, CreateView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = EventCategory
    fields = ['name', 'code', 'image', 'priority', 'status']
    template_name = 'events/create_event_category.html'

    def form_valid(self, form):
        form.instance.created_user = self.request.user
        form.instance.updated_user = self.request.user
        return super().form_valid(form)


class EventCategoryUpdateView(RoleRequiredMixin, LoginRequiredMixin, UpdateView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = EventCategory
    fields = ['name', 'code', 'image', 'priority', 'status']
    template_name = 'events/edit_event_category.html'

    def form_valid(self, form):
        form.instance.updated_user = self.request.user
        return super().form_valid(form)


class EventCategoryDeleteView(RoleRequiredMixin, LoginRequiredMixin, DeleteView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model =  EventCategory
    template_name = 'events/event_category_delete.html'
    success_url = reverse_lazy('event-category-list')

@login_required(login_url='login')
@role_required('admin', 'faculty', 'staff')
def create_event(request):
    event_form = EventForm()
    event_image_form = EventImageForm()
    event_agenda_form = EventAgendaForm()
    catg = EventCategory.objects.all()
    if request.method == 'POST':
        event_form = EventForm(request.POST)
        event_image_form = EventImageForm(request.POST, request.FILES)
        event_agenda_form = EventAgendaForm(request.POST)
        if event_form.is_valid() and event_image_form.is_valid() and event_agenda_form.is_valid():
            ef = event_form.save()
            created_updated(Event, request)
            event_image_form.save(commit=False)
            event_image_form.event_form = ef
            event_image_form.save()
            
            event_agenda_form.save(commit=False)
            event_agenda_form.event_form = ef
            event_agenda_form.save()
            return redirect('event-list')
    context = {
        'form': event_form,
        'form_1': event_image_form,
        'form_2': event_agenda_form,
        'ctg': catg
    }
    return render(request, 'events/create.html', context)

class EventCreateView(RoleRequiredMixin, LoginRequiredMixin, CreateView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    form_class = EventCreateMultiForm
    template_name = 'events/create_event.html'
    success_url = reverse_lazy('event-list')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            _ensure_default_event_categories(request.user)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        evt = form['event'].save(commit=False)
        evt.created_user = self.request.user
        evt.updated_user = self.request.user
        evt.save()
        # Event image optional: only save if a file was uploaded
        event_image = form['event_image'].save(commit=False)
        event_image.event = evt
        if form['event_image'].cleaned_data.get('image'):
            event_image.save()
        else:
            event_image.image = None
            event_image.save()

        event_agenda = form['event_agenda'].save(commit=False)
        event_agenda.event = evt
        event_agenda.save()

        self.object = evt
        return HttpResponseRedirect(self.get_success_url())
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['ctg'] = EventCategory.objects.all()
        return context


class EventListView(RoleRequiredMixin, LoginRequiredMixin, ListView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = timezone.localdate()
        return context


@login_required(login_url='login')
def event_edit(request, pk):
    """Edit event: main form + image + agenda formset (multiple rows). Locked when event end_date has passed."""
    from gate_analytics.roles import has_role
    if not has_role(request.user, 'admin', 'faculty', 'staff'):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 Forbidden</h1>')
    event = get_object_or_404(Event, pk=pk)
    if event.end_date < timezone.localdate():
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('<h1>403 Forbidden</h1><p>Editing is locked for events that have already ended.</p>')
    form = EventForm(request.POST or None, instance=event)
    try:
        event_image = event.eventimage
    except EventImage.DoesNotExist:
        event_image = None
    image_form = EventImageForm(request.POST or None, request.FILES or None, instance=event_image)
    agenda_formset = EventAgendaFormSet(request.POST or None, instance=event)
    if request.method == 'POST':
        if form.is_valid() and image_form.is_valid() and agenda_formset.is_valid():
            evt = form.save(commit=False)
            evt.updated_user = request.user
            evt.save()
            if event_image:
                image_form.save()
            elif image_form.cleaned_data.get('image'):
                EventImage.objects.create(event=evt, image=image_form.cleaned_data['image'])
            agenda_formset.save()
            return redirect('event-detail', pk=evt.pk)
    return render(request, 'events/edit_event.html', {
        'form': form,
        'image_form': image_form,
        'agenda_formset': agenda_formset,
        'event': event,
    })


class EventDetailView(RoleRequiredMixin, LoginRequiredMixin, DetailView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.utils import timezone
        context['today'] = timezone.localdate()
        return context


class EventDeleteView(LoginRequiredMixin, DeleteView):
    login_url = 'login'
    model = Event
    template_name = 'events/delete_event.html'
    success_url = reverse_lazy('event-list')


class AddEventMemberCreateView(RoleRequiredMixin, LoginRequiredMixin, CreateView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = EventMember
    fields = ['event', 'user', 'attend_status', 'status']
    template_name = 'events/add_event_member.html'

    def form_valid(self, form):
        form.instance.created_user = self.request.user
        form.instance.updated_user = self.request.user
        return super().form_valid(form)


class JoinEventListView(RoleRequiredMixin, LoginRequiredMixin, ListView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = EventMember
    template_name = 'events/joinevent_list.html'
    context_object_name = 'eventmember'


class RemoveEventMemberDeleteView(RoleRequiredMixin, LoginRequiredMixin, DeleteView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = EventMember
    template_name = 'events/remove_event_member.html'
    success_url = reverse_lazy('join-event-list')


class EventUserWishListView(RoleRequiredMixin, LoginRequiredMixin, ListView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = EventUserWishList
    template_name = 'events/event_user_wish_list.html'
    context_object_name = 'eventwish'


class AddEventUserWishListCreateView(RoleRequiredMixin, LoginRequiredMixin, CreateView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = EventUserWishList
    fields = ['event', 'user', 'status']
    template_name = 'events/add_event_user_wish.html'

    def form_valid(self, form):
        form.instance.created_user = self.request.user
        form.instance.updated_user = self.request.user
        return super().form_valid(form)


class RemoveEventUserWishDeleteView(RoleRequiredMixin, LoginRequiredMixin, DeleteView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = EventUserWishList
    template_name = 'events/remove_event_user_wish.html'
    success_url = reverse_lazy('event-wish-list')


class UpdateEventStatusView(RoleRequiredMixin, LoginRequiredMixin, UpdateView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = Event
    form_class = EventStatusForm
    template_name = 'events/update_event_status.html'
    success_url = reverse_lazy('event-list')


class CompleteEventList(RoleRequiredMixin, LoginRequiredMixin, ListView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = Event
    template_name = 'events/complete_event_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        return Event.objects.filter(status='completed')


class AbsenseUserList(RoleRequiredMixin, LoginRequiredMixin, ListView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = EventMember
    template_name = 'events/absense_user_list.html'
    context_object_name = 'absenseuser'

    def get_queryset(self):
        return EventMember.objects.filter(attend_status='absent')


class CompleteEventUserList(RoleRequiredMixin, LoginRequiredMixin, ListView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = EventMember
    template_name = 'events/complete_event_user_list.html'
    context_object_name = 'completeuser'

    def get_queryset(self):
        return EventMember.objects.filter(attend_status='completed')


class CreateUserMark(RoleRequiredMixin, LoginRequiredMixin, CreateView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = UserCoin
    fields = ['user', 'gain_type', 'gain_coin', 'status']
    template_name = 'events/create_user_mark.html'

    def form_valid(self, form):
        form.instance.created_user = self.request.user
        form.instance.updated_user = self.request.user
        return super().form_valid(form)


class UserMarkList(RoleRequiredMixin, LoginRequiredMixin, ListView):
    allowed_roles = EVENT_ROLES
    login_url = 'login'
    model = UserCoin
    template_name = 'events/user_mark_list.html'
    context_object_name = 'usermark'


@login_required(login_url='login')
@role_required('admin', 'faculty', 'staff')
def search_event_category(request):
    if request.method == 'POST':
       data = request.POST['search']
       event_category = EventCategory.objects.filter(name__icontains=data)
       context = {
           'event_category': event_category
       }
       return render(request, 'events/event_category.html', context)
    return render(request, 'events/event_category.html')

@login_required(login_url='login')
@role_required('admin', 'faculty', 'staff')
def search_event(request):
    if request.method == 'POST':
       data = request.POST['search']
       events = Event.objects.filter(name__icontains=data)
       context = {
           'events': events,
           'today': timezone.localdate(),
       }
       return render(request, 'events/event_list.html', context)
    context = {'events': Event.objects.all(), 'today': timezone.localdate()}
    return render(request, 'events/event_list.html', context) 
    
