from django.utils import timezone
from datetime import datetime, date
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from master_admin.models import Event, Category, UserRole, User

TOTAL_AMOUNT_ALLOCATED = "Tổng số tiền được cấp trong năm"
AMOUNT_ALLOCATED_PERSON = "Số tiền được cấp trên người"


def admin_required(view_func):
    """Decorator để kiểm tra user có phải admin"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            user_role = getattr(request.user, 'role', UserRole.ADMIN)
            if user_role == UserRole.ADMIN:
                return view_func(request, *args, **kwargs)
        return redirect('user_dashboard')
    return wrapper


def custom_login_view(request):
    if request.method == 'POST':
        # 1. Đổi 'email' thành 'username' để lấy dữ liệu từ form
        username = request.POST.get('username')
        password = request.POST.get('password')

        # 2. Quan trọng nhất: Hàm authenticate phải dùng tham số username=...
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Redirect dựa trên role của user (user cũ được set default là ADMIN)
            user_role = getattr(user, 'role', UserRole.ADMIN)
            if user_role == UserRole.ADMIN:
                return redirect('admin_dashboard')
            else:
                return redirect('user_dashboard')
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'loginAdmin.html', context={})


@login_required(login_url='/login/')
@admin_required
def admin_dashboard(request):
    """Dashboard cho admin"""
    today = date.today()
    total_events = Event.objects.filter(is_adhoc=False, toDate__gte=today).count()  # Sự kiện dự kiến
    adhoc_events = Event.objects.filter(is_adhoc=True).count()  # Sự kiện phát sinh
    completed_events = Event.objects.filter(toDate__lt=today).count()  # Sự kiện đã diễn ra
    
    context = {
        'total_events': total_events,
        'adhoc_events': adhoc_events,
        'completed_events': completed_events,
    }
    return render(request, 'admin_dashboard.html', context)


@login_required(login_url='/login/')
@admin_required
def create_user(request):
    """Tạo user thường mới (chỉ admin mới được tạo)"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if username and email and password:
            # Kiểm tra username đã tồn tại chưa
            if User.objects.filter(username=username).exists():
                messages.error(request, f"Tên đăng nhập '{username}' đã tồn tại!")
            elif User.objects.filter(email=email).exists():
                messages.error(request, f"Email '{email}' đã được sử dụng!")
            else:
                # Tạo user mới với role USER
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    role=UserRole.USER
                )
                messages.success(request, f"Đã tạo user '{username}' thành công!")
        else:
            messages.error(request, "Vui lòng điền đầy đủ thông tin!")
    
    return redirect('admin_dashboard')


@login_required(login_url='/login/')
def user_dashboard(request):
    """Dashboard cho user thường"""
    # User thường chỉ xem được các sự kiện dự kiến chưa diễn ra
    today = date.today()
    upcoming_events = Event.objects.filter(is_adhoc=False, toDate__gte=today).order_by('fromDate')
    
    context = {
        'upcoming_events': upcoming_events,
    }
    return render(request, 'user_dashboard.html', context)


@login_required(login_url='/login/')
@admin_required
def quan_ly_view(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')

        title = request.POST.get('title')
        fromDate = request.POST.get('fromDate')
        toDate = request.POST.get('toDate')
        year = request.POST.get('year')
        totalUserAllocated = request.POST.get('totalUserAllocated')
        totalAmount = request.POST.get('totalAmount', '0')
        cleanAmount = totalAmount.replace('.', '').strip()
        danh_muc_ids = request.POST.getlist('danh_muc')

        if title and fromDate and toDate:
            if event_id:
                event = get_object_or_404(Event, id=event_id)
                event.title = title
                event.fromDate = fromDate
                event.toDate = toDate
                event.year = year
                event.totalAmount = cleanAmount
                event.totalUserAllocated = totalUserAllocated
                event.is_adhoc = False
                event.save()
                event.categories.set(danh_muc_ids)
                messages.success(request, "Cập nhật sự kiện thành công!")
            else:
                new_event = Event.objects.create(
                    title=title,
                    fromDate=fromDate,
                    toDate=toDate,
                    totalUserAllocated=totalUserAllocated,
                    totalAmount=cleanAmount,
                    year=year,
                    is_adhoc=False,
                )
                new_event.categories.set(danh_muc_ids)
                messages.success(request, "Thêm sự kiện mới thành công!")

            # Kiểm tra ngày kết thúc để redirect tới trang phù hợp
            to_date_obj = datetime.strptime(toDate, '%Y-%m-%d').date()
            today = date.today()
            
            if to_date_obj < today:
                return redirect('quanLySuKienDaDienRa')
            else:
                return redirect('quanLySuKien')
        else:
            messages.error(request, "Vui lòng điền đầy đủ thông tin.")

    current_year = timezone.now().year
    all_categories = Category.objects.all().exclude(Q(name=TOTAL_AMOUNT_ALLOCATED) | Q(name=AMOUNT_ALLOCATED_PERSON))
    per_user_amount = Category.objects.filter(name=AMOUNT_ALLOCATED_PERSON, year=str(current_year)).first().amount
    total_amount = Category.objects.filter(name=TOTAL_AMOUNT_ALLOCATED, year=str(current_year)).first().amount

    selected_year = request.GET.get('year')
    available_years = Event.objects.values_list('year', flat=True).distinct().order_by('-year')

    # Chỉ hiển thị sự kiện dự kiến (chưa diễn ra)
    today = date.today()
    events = Event.objects.filter(is_adhoc=False, toDate__gte=today).order_by('-fromDate')
    if selected_year:
        events = events.filter(year=selected_year)

    context = {
        'all_categories': all_categories,
        'events': events,
        'per_user_amount': per_user_amount,
        'totalAmountYear': total_amount,
        'available_years': available_years,
        'selected_year': selected_year,
    }
    return render(request, 'quanLySuKien.html', context)


@login_required(login_url='/login/')
@admin_required
def quan_ly_da_dien_ra_view(request):
    current_year = timezone.now().year
    today = date.today()
    
    all_categories = Category.objects.all().exclude(Q(name=TOTAL_AMOUNT_ALLOCATED) | Q(name=AMOUNT_ALLOCATED_PERSON))
    per_user_amount = Category.objects.filter(name=AMOUNT_ALLOCATED_PERSON, year=str(current_year)).first().amount
    total_amount = Category.objects.filter(name=TOTAL_AMOUNT_ALLOCATED, year=str(current_year)).first().amount

    selected_year = request.GET.get('year')
    available_years = Event.objects.values_list('year', flat=True).distinct().order_by('-year')

    # Lọc các sự kiện đã diễn ra (toDate < hôm nay)
    events = Event.objects.filter(toDate__lt=today).order_by('-toDate')
    if selected_year:
        events = events.filter(year=selected_year)

    context = {
        'all_categories': all_categories,
        'events': events,
        'per_user_amount': per_user_amount,
        'totalAmountYear': total_amount,
        'available_years': available_years,
        'selected_year': selected_year,
    }
    return render(request, 'quanLySuKienDaDienRa.html', context)


@login_required(login_url='/login/')
@admin_required
def quan_ly_su_kien_phat_sinh_view(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        is_adhoc = request.POST.get('is_adhoc', '0')

        title = request.POST.get('title')
        fromDate = request.POST.get('fromDate')
        toDate = request.POST.get('toDate')
        year = request.POST.get('year')
        totalUserAllocated = request.POST.get('totalUserAllocated')
        totalAmount = request.POST.get('totalAmount', '0')
        cleanAmount = totalAmount.replace('.', '').strip()
        danh_muc_ids = request.POST.getlist('danh_muc')

        if title and fromDate and toDate:
            if event_id:
                event = get_object_or_404(Event, id=event_id)
                event.title = title
                event.fromDate = fromDate
                event.toDate = toDate
                event.year = year
                event.totalAmount = cleanAmount
                event.totalUserAllocated = totalUserAllocated
                event.is_adhoc = True if is_adhoc == '1' else False
                event.save()
                event.categories.set(danh_muc_ids)
                messages.success(request, "Cập nhật sự kiện phát sinh thành công!")
            else:
                new_event = Event.objects.create(
                    title=title,
                    fromDate=fromDate,
                    toDate=toDate,
                    totalUserAllocated=totalUserAllocated,
                    totalAmount=cleanAmount,
                    year=year,
                    is_adhoc=True,
                    is_reviewed=False,
                )
                new_event.categories.set(danh_muc_ids)
                messages.success(request, "Thêm sự kiện phát sinh mới thành công! Sự kiện sẽ chờ duyệt.")

            # Kiểm tra ngày kết thúc để redirect tới trang phù hợp
            to_date_obj = datetime.strptime(toDate, '%Y-%m-%d').date()
            today = date.today()
            
            if to_date_obj < today:
                return redirect('quanLySuKienDaDienRa')
            else:
                return redirect('duyetSuKien')
        else:
            messages.error(request, "Vui lòng điền đầy đủ thông tin.")

    current_year = timezone.now().year
    all_categories = Category.objects.all().exclude(Q(name=TOTAL_AMOUNT_ALLOCATED) | Q(name=AMOUNT_ALLOCATED_PERSON))
    per_user_amount = Category.objects.filter(name=AMOUNT_ALLOCATED_PERSON, year=str(current_year)).first().amount
    total_amount = Category.objects.filter(name=TOTAL_AMOUNT_ALLOCATED, year=str(current_year)).first().amount

    selected_year = request.GET.get('year')
    available_years = Event.objects.values_list('year', flat=True).distinct().order_by('-year')

    # Lọc các sự kiện phát sinh đã được duyệt và chưa diễn ra
    today = date.today()
    events = Event.objects.filter(is_adhoc=True, is_reviewed=True, toDate__gte=today).order_by('-fromDate')
    if selected_year:
        events = events.filter(year=selected_year)

    context = {
        'all_categories': all_categories,
        'events': events,
        'per_user_amount': per_user_amount,
        'totalAmountYear': total_amount,
        'available_years': available_years,
        'selected_year': selected_year,
    }
    return render(request, 'quanLySuKienPhatSinh.html', context)


@login_required(login_url='/login/')
@admin_required
def duyet_su_kien_view(request):
    current_year = timezone.now().year
    all_categories = Category.objects.all().exclude(Q(name=TOTAL_AMOUNT_ALLOCATED) | Q(name=AMOUNT_ALLOCATED_PERSON))
    per_user_amount = Category.objects.filter(name=AMOUNT_ALLOCATED_PERSON, year=str(current_year)).first().amount
    total_amount = Category.objects.filter(name=TOTAL_AMOUNT_ALLOCATED, year=str(current_year)).first().amount

    selected_year = request.GET.get('year')
    available_years = Event.objects.values_list('year', flat=True).distinct().order_by('-year')

    today = date.today()
    events = Event.objects.filter(is_adhoc=True, is_reviewed=False, toDate__gte=today).order_by('-fromDate')
    if selected_year:
        events = events.filter(year=selected_year)

    context = {
        'all_categories': all_categories,
        'events': events,
        'per_user_amount': per_user_amount,
        'totalAmountYear': total_amount,
        'available_years': available_years,
        'selected_year': selected_year,
    }
    return render(request, 'duyetSuKien.html', context)


@login_required(login_url='/login/')
@admin_required
def phe_duyet_su_kien_view(request, event_id):
    if request.method == 'POST':
        event = get_object_or_404(Event, id=event_id, is_adhoc=True, is_reviewed=False)
        event.is_reviewed = True
        event.save()
        messages.success(request, 'Sự kiện đã được duyệt thành công!')
    return redirect('duyetSuKien')


@login_required(login_url='/login/')
@admin_required
def khong_duyet_su_kien_view(request, event_id):
    if request.method == 'POST':
        event = get_object_or_404(Event, id=event_id, is_adhoc=True, is_reviewed=False)
        event.delete()  # Xóa sự kiện thay vì reject
        messages.warning(request, 'Sự kiện đã bị từ chối và xóa khỏi hệ thống!')
    return redirect('duyetSuKien')


def get_categories_by_year(request):
    year = request.GET.get('year')
    if year:
        per_user_amount = 0
        totalAmountYear = 0
        categories = Category.objects.filter(year=year).values('id', 'name', 'amount').exclude(
            Q(name=TOTAL_AMOUNT_ALLOCATED) | Q(name=AMOUNT_ALLOCATED_PERSON))
        per_user = Category.objects.filter(name=AMOUNT_ALLOCATED_PERSON, year=year).first()
        total_amount = Category.objects.filter(name=TOTAL_AMOUNT_ALLOCATED, year=year).first()
        if per_user:
            per_user_amount = per_user.amount
        if total_amount:
            totalAmountYear = total_amount.amount
        categories_list = list(categories)

        return JsonResponse({'categories': categories_list,
                             'per_user_amount': per_user_amount,
                             'totalAmountYear': totalAmountYear,
                             }, safe=False)


    return JsonResponse({'categories': []}, status=400)


@login_required(login_url='/login/')
@admin_required
def xoa_su_kien_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    event.delete()
    messages.success(request, "Đã xóa sự kiện thành công!")
    return redirect('quanLySuKien')


@login_required(login_url='/login/')
@admin_required
def quan_ly_danh_muc_view(request):
    if request.method == 'POST':
        cat_id = request.POST.get('id')
        name = request.POST.get('name')
        from_date = request.POST.get('fromDate')
        to_date = request.POST.get('toDate')
        year = request.POST.get('year')

        raw_amount = request.POST.get('amount', '0')
        clean_amount = raw_amount.replace('.', '').replace(',', '').strip()

        if name and clean_amount and from_date and to_date:
            try:
                if cat_id:
                    category = get_object_or_404(Category, id=cat_id)
                    category.name = name
                    category.amount = clean_amount
                    category.fromDate = from_date
                    category.toDate = to_date
                    category.year = year
                    category.save()
                    messages.success(request, "Cập nhật tiêu chí thành công!")
                else:
                    Category.objects.create(
                        name=name,
                        amount=clean_amount,
                        fromDate=from_date,
                        toDate=to_date,
                        year=year
                    )
                    messages.success(request, "Thêm tiêu chí mới thành công!")

                return redirect('quanLyDanhMuc')
            except Exception as e:
                messages.error(request, f"Lỗi hệ thống: {e}")
        else:
            messages.error(request, "Vui lòng nhập đầy đủ: Tên, Số tiền và cả hai Ngày.")

    selected_year = request.GET.get('year')

    all_categories = Category.objects.all().order_by('-id')

    if selected_year and selected_year.strip():
        all_categories = all_categories.filter(year=selected_year)

    available_years = Category.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'danhMuc.html', {
        'all_categories': all_categories,
        'available_years': available_years,
        'selected_year': selected_year
    })


@login_required(login_url='/login/')
@admin_required
def xoa_tieu_chi(request, id):
    category = get_object_or_404(Category, id=id)
    category.delete()
    messages.success(request, "Xóa thành công!")
    return redirect('quanLyDanhMuc')


def logout_view(request):
    logout(request)
    return redirect('login')