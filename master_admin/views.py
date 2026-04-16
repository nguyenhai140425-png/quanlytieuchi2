from django.utils import timezone
from datetime import datetime, date
from functools import wraps
from master_admin.models import EventCategory
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from master_admin.models import Event, Category, UserRole, User, EventApprovalStatus

TOTAL_AMOUNT_ALLOCATED = "Tổng số tiền được cấp trong năm"
AMOUNT_ALLOCATED_PERSON = "Số tiền được cấp trên người"


def _get_fixed_category_amount(category_name):
    category = Category.objects.filter(name=category_name).only('amount').first()
    if not category or category.amount is None:
        return 0
    return float(category.amount)


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
    return render(request, 'admin_dashboard.html')


@login_required(login_url='/login/')
@admin_required
def quan_ly_nguoi_dung_view(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if user_id:
            # Edit user
            user = get_object_or_404(User, id=user_id)
            if user.username != username and User.objects.filter(username=username).exists():
                messages.error(request, f"Tên đăng nhập '{username}' đã tồn tại!")
            elif user.email != email and User.objects.filter(email=email).exists():
                messages.error(request, f"Email '{email}' đã được sử dụng!")
            else:
                user.username = username
                user.email = email
                if password:
                    user.set_password(password)
                user.save()
                messages.success(request, "Cập nhật người dùng thành công!")
        else:
            # Add user
            if User.objects.filter(username=username).exists():
                messages.error(request, f"Tên đăng nhập '{username}' đã tồn tại!")
            elif User.objects.filter(email=email).exists():
                messages.error(request, f"Email '{email}' đã được sử dụng!")
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    role=UserRole.USER
                )
                messages.success(request, f"Đã tạo người dùng '{username}' thành công!")
        
        return redirect('quanLyNguoiDung')
    
    users = User.objects.filter(role=UserRole.USER).order_by('-id')
    return render(request, 'quanLyNguoiDung.html', {'users': users})


@login_required(login_url='/login/')
@admin_required
def xoa_nguoi_dung_view(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            messages.error(request, "Không thể xóa tài khoản của chính mình!")
        else:
            user.delete()
            messages.success(request, "Đã xóa người dùng thành công!")
    return redirect('quanLyNguoiDung')


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
    if request.method == 'POST':
        title = request.POST.get('title')
        fromDate = request.POST.get('fromDate')
        toDate = request.POST.get('toDate')
        year = request.POST.get('year')
        totalUserAllocated = request.POST.get('totalUserAllocated')
        totalAmount = request.POST.get('totalAmount', '0')
        # 🔥 Xử lý định dạng tiền tệ Việt Nam (1.234.567,89 -> 1234567.89)
        cleanAmount = totalAmount.replace('.', '').replace(',', '.').strip()
        danh_muc_ids = request.POST.getlist('danh_muc')

        if title and fromDate and toDate:
            new_event = Event.objects.create(
                title=title,
                fromDate=fromDate,
                toDate=toDate,
                totalUserAllocated=totalUserAllocated,
                totalAmount=cleanAmount,
                year=year,
  
                is_adhoc=True,   # 🔥 User tạo sẽ là sự kiện phát sinh luôn, chờ admin duyệt
                approval_status=EventApprovalStatus.PENDING
            )
            new_event.categories.set(danh_muc_ids)
            messages.success(request, "Đã gửi yêu cầu tạo sự kiện! Chờ admin duyệt.")
        else:
            messages.error(request, "Vui lòng điền đầy đủ thông tin!")

    # User thường chỉ xem được các sự kiện dự kiến chưa diễn ra
    today = date.today()
    upcoming_events = Event.objects.filter(
    is_adhoc=False,
    toDate__gte=today,
    approval_status=EventApprovalStatus.APPROVED   # 👈 FIX QUAN TRỌNG
).order_by('fromDate')
    categories = Category.objects.all()
    
    context = {
        'upcoming_events': upcoming_events,
        'categories': categories,
    }
    return render(request, 'user_dashboard.html', context)

@login_required(login_url='/login/')
@admin_required
def quan_ly_view(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        parent_event_id = request.POST.get('parent_event_id')
        is_child_mode = request.POST.get('is_child_mode') == '1'

        title = request.POST.get('title')
        fromDate = request.POST.get('fromDate')
        toDate = request.POST.get('toDate')
        year = request.POST.get('year')
        totalUserAllocated = request.POST.get('totalUserAllocated')

        danh_muc_ids = request.POST.getlist('danh_muc')

        if title and fromDate and toDate:
            if is_child_mode:
                parent_event = get_object_or_404(Event, id=parent_event_id)

                event = Event.objects.create(
                    title=title,
                    fromDate=fromDate,
                    toDate=toDate,
                    year=parent_event.year,
                    totalUserAllocated=parent_event.totalUserAllocated,
                    totalAmount=parent_event.totalAmount,
                    is_adhoc=parent_event.is_adhoc,
                    parent_event=parent_event,
                    approval_status=parent_event.approval_status,
                )

                # Inherit categories from parent event
                parent_categories = EventCategory.objects.filter(event=parent_event)
                for parent_category in parent_categories:
                    EventCategory.objects.create(
                        event=event,
                        category=parent_category.category,
                        quantity=parent_category.quantity,
                    )

                messages.success(request, "Lưu sự kiện con thành công!")
            else:
                if event_id:
                    event = get_object_or_404(Event, id=event_id)
                    event.title = title
                    event.fromDate = fromDate
                    event.toDate = toDate
                    event.year = year
                    event.totalUserAllocated = totalUserAllocated
                    event.is_adhoc = False
                    # 🔥 ĐỬNG SAVE TỪ ĐÂY - LƯU SAU KHI TÍNH TOTAL
                else:
                    event = Event.objects.create(
                        title=title,
                        fromDate=fromDate,
                        toDate=toDate,
                        totalUserAllocated=totalUserAllocated,
                        year=year,
                        is_adhoc=False,
                        totalAmount=0,  # 🔥 SET MẶC ĐỊNH 0 TRC TÍNH TOÁN
                    )

                # 🔥 IMPORT
                from master_admin.models import EventCategory

                # 🔥 XÓA DỮ LIỆU CŨ (khi edit)
                EventCategory.objects.filter(event=event).delete()

                total = 0

                # 🔥 LẤY TIỀN / NGƯỜI
                money_per_person = Category.objects.get(
                    name="Số tiền được cấp trên người"
                ).amount

                total += int(totalUserAllocated) * float(money_per_person)

                # 🔥 XỬ LÝ TIÊU CHÍ
                for cat_id in danh_muc_ids:
                    category = Category.objects.get(id=cat_id)

                    # lưu DB (quantity mặc định = 1 vì frontend chỉ select/deselect)
                    EventCategory.objects.create(
                        event=event,
                        category=category,
                        quantity=1
                    )

                    # 🔥 CỘNG TRỰC TIẾP AMOUNT (không nhân quantity)
                    total += float(category.amount)

                # 🔥 CẬP NHẬT TOTAL VÀ LƯU (LẦN DUY NHẤT)
                event.totalAmount = total
                event.save()

                messages.success(request, "Lưu sự kiện thành công!")

            # 🔥 redirect
            to_date_obj = datetime.strptime(toDate, '%Y-%m-%d').date()
            today = date.today()

            if to_date_obj < today:
                return redirect('quanLySuKienDaDienRa')
            else:
                return redirect('quanLySuKien')

        else:
            messages.error(request, "Vui lòng điền đầy đủ thông tin.")

    # 🔥 LẤY CATEGORY (BỎ 2 CÁI FIXED)
    all_categories = Category.objects.exclude(
    Q(name=TOTAL_AMOUNT_ALLOCATED) |
    Q(name=AMOUNT_ALLOCATED_PERSON)
)
    today = date.today()
    events = Event.objects.filter(
        is_adhoc=False,
        approval_status=EventApprovalStatus.APPROVED,
        toDate__gte=today
    ).order_by('-fromDate')

    context = {
        'all_categories': all_categories,
        'events': events,
        'per_user_amount': _get_fixed_category_amount(AMOUNT_ALLOCATED_PERSON),
        'totalAmountYear': _get_fixed_category_amount(TOTAL_AMOUNT_ALLOCATED),
    }

    return render(request, 'quanLySuKien.html', context)

@login_required(login_url='/login/')
@admin_required
def quan_ly_da_dien_ra_view(request):
    today = date.today()
    
    all_categories = Category.objects.all().exclude(Q(name=TOTAL_AMOUNT_ALLOCATED) | Q(name=AMOUNT_ALLOCATED_PERSON))

    # Lọc các sự kiện đã diễn ra (toDate < hôm nay)
#    events = Event.objects.filter(toDate__lt=today).order_by('-toDate')
    events = Event.objects.filter(is_adhoc=False,approval_status=EventApprovalStatus.APPROVED,
    toDate__lt=today).order_by('-toDate')
    context = {
        'all_categories': all_categories,
        'events': events,
    }
    return render(request, 'quanLySuKienDaDienRa.html', context)



@login_required(login_url='/login/')
@admin_required
def quan_ly_su_kien_phat_sinh_view(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        title = request.POST.get('title')
        fromDate = request.POST.get('fromDate')
        toDate = request.POST.get('toDate')
        year = request.POST.get('year')
        totalUserAllocated = request.POST.get('totalUserAllocated')
        danh_muc_ids = request.POST.getlist('danh_muc')

        if title and fromDate and toDate:
            if event_id:
                # Edit existing event
                event = get_object_or_404(Event, id=event_id)
                event.title = title
                event.fromDate = fromDate
                event.toDate = toDate
                event.year = year
                event.totalUserAllocated = totalUserAllocated
                event.is_adhoc = True
                # 🔥 KHÔNG SAVE TỪ ĐÂY - LƯU SAU KHI TÍNH TOTAL
            else:
                # Create new event
                event = Event.objects.create(
                    title=title,
                    fromDate=fromDate,
                    toDate=toDate,
                    totalUserAllocated=totalUserAllocated,
                    year=year,
                    is_adhoc=True,
                    approval_status=EventApprovalStatus.APPROVED,
                    totalAmount=0,  # 🔥 SET MẶC ĐỊNH 0 TRC TÍNH TOÁN
                )

            # 🔥 XÓA DỮ LIỆU CŨ (khi edit)
            EventCategory.objects.filter(event=event).delete()

            total = 0

            # 🔥 LẤY TIỀN / NGƯỜI
            money_per_person = Category.objects.get(
                name="Số tiền được cấp trên người"
            ).amount

            total += int(totalUserAllocated) * float(money_per_person)

            # 🔥 XỬ LÝ TIÊU CHÍ
            for cat_id in danh_muc_ids:
                category = Category.objects.get(id=cat_id)

                # lưu DB (quantity mặc định = 1 vì frontend chỉ select/deselect)
                EventCategory.objects.create(
                    event=event,
                    category=category,
                    quantity=1
                )

                # 🔥 CỘNG TRỰC TIẾP AMOUNT (không nhân quantity)
                total += float(category.amount)

            # 🔥 CẬP NHẬT TOTAL
            event.totalAmount = total
            event.save()

            messages.success(request, "Lưu sự kiện phát sinh thành công!")
            return redirect('quanLySuKienPhatSinh')
        else:
            messages.error(request, "Vui lòng điền đầy đủ thông tin!")

    all_categories = Category.objects.all().exclude(
        Q(name=TOTAL_AMOUNT_ALLOCATED) |
        Q(name=AMOUNT_ALLOCATED_PERSON)
    )
    today = date.today()
    events = Event.objects.filter(
        is_adhoc=True,
        approval_status__in=[
            EventApprovalStatus.APPROVED,
            EventApprovalStatus.REJECTED
        ],
        toDate__gte=today
    ).order_by('-fromDate')

    context = {
        'all_categories': all_categories,
        'events': events,
        'per_user_amount': _get_fixed_category_amount(AMOUNT_ALLOCATED_PERSON),
        'totalAmountYear': _get_fixed_category_amount(TOTAL_AMOUNT_ALLOCATED),
    }

    return render(request, 'quanLySuKienPhatSinh.html', context)


@login_required(login_url='/login/')
@admin_required
def duyet_su_kien_view(request):
    today = date.today()

    events = Event.objects.filter(
        is_adhoc=True,
        approval_status=EventApprovalStatus.PENDING
    ).order_by('-fromDate')

    return render(request, 'duyetSuKien.html', {
        'events': events
    })


@login_required(login_url='/login/')
@admin_required
def phe_duyet_su_kien_view(request, event_id):
    if request.method == 'POST':
        event = Event.objects.filter(id=event_id).first()
        if not event:
            messages.error(request, 'Không tìm thấy sự kiện để duyệt.')
            return redirect('duyetSuKien')

        if event.approval_status != EventApprovalStatus.PENDING:
            messages.warning(request, 'Sự kiện này đã được xử lý trước đó.')
            return redirect('duyetSuKien')

        event.approval_status = EventApprovalStatus.APPROVED
        # 🔥 GIỮ NGUYÊN is_adhoc=True → để vào "sự kiện phát sinh"
        event.is_adhoc = True
        event.save()

        messages.success(request, 'Đã duyệt! Sự kiện đã chuyển sang mục phát sinh.')

    return redirect('duyetSuKien')


@login_required(login_url='/login/')
@admin_required
def khong_duyet_su_kien_view(request, event_id):
    if request.method == 'POST':
        event = Event.objects.filter(id=event_id).first()
        if not event:
            messages.error(request, 'Không tìm thấy sự kiện để từ chối.')
            return redirect('duyetSuKien')

        if event.approval_status != EventApprovalStatus.PENDING:
            messages.warning(request, 'Sự kiện này đã được xử lý trước đó.')
            return redirect('duyetSuKien')

        event.approval_status = EventApprovalStatus.REJECTED
        event.save()

        messages.warning(request, 'Sự kiện đã bị từ chối.')

    return redirect('duyetSuKien')
def get_categories(request):
    categories = Category.objects.all().values('id', 'name', 'amount').exclude(
        Q(name=TOTAL_AMOUNT_ALLOCATED) | Q(name=AMOUNT_ALLOCATED_PERSON))
    categories_list = list(categories)

    return JsonResponse({
        'categories': categories_list,
        'per_user_amount': _get_fixed_category_amount(AMOUNT_ALLOCATED_PERSON),
        'totalAmountYear': _get_fixed_category_amount(TOTAL_AMOUNT_ALLOCATED),
    }, safe=False)


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

    all_categories = Category.objects.all().order_by('-id')

    return render(request, 'danhMuc.html', {
        'all_categories': all_categories,
    })


@login_required(login_url='/login/')
@admin_required
def xoa_nguoi_dung(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        messages.error(request, "Không thể xóa tài khoản của chính mình!")
    else:
        user.delete()
        messages.success(request, f"Đã xóa người dùng '{user.username}' thành công!")
    return redirect('quanLyNguoiDung')


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
