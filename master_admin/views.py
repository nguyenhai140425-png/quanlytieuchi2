from django.utils import timezone

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from master_admin.models import Event, Category

TOTAL_AMOUNT_ALLOCATED = "Tổng số tiền được cấp trong năm"
AMOUNT_ALLOCATED_PERSON = "Số tiền được cấp trên người"


def custom_login_view(request):
    if request.method == 'POST':
        # 1. Đổi 'email' thành 'username' để lấy dữ liệu từ form
        username = request.POST.get('username')
        password = request.POST.get('password')

        # 2. Quan trọng nhất: Hàm authenticate phải dùng tham số username=...
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('quanLySuKien')
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'loginAdmin.html', context={})

@login_required(login_url='/login/')
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
                )
                new_event.categories.set(danh_muc_ids)
                messages.success(request, "Thêm sự kiện mới thành công!")

            return redirect('quanLySuKien')
        else:
            messages.error(request, "Vui lòng điền đầy đủ thông tin.")

    current_year = timezone.now().year
    all_categories = Category.objects.all().exclude(Q(name=TOTAL_AMOUNT_ALLOCATED) | Q(name=AMOUNT_ALLOCATED_PERSON))
    per_user_amount = Category.objects.filter(name=AMOUNT_ALLOCATED_PERSON, year=str(current_year)).first().amount
    total_amount = Category.objects.filter(name=TOTAL_AMOUNT_ALLOCATED, year=str(current_year)).first().amount

    selected_year = request.GET.get('year')
    available_years = Event.objects.values_list('year', flat=True).distinct().order_by('-year')

    events = Event.objects.all().order_by('-fromDate')
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
def xoa_su_kien_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    event.delete()
    messages.success(request, "Đã xóa sự kiện thành công!")
    return redirect('quanLySuKien')


@login_required(login_url='/login/')
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
def xoa_tieu_chi(request, id):
    category = get_object_or_404(Category, id=id)
    category.delete()
    messages.success(request, "Xóa thành công!")
    return redirect('quanLyDanhMuc')


def logout_view(request):
    logout(request)
    return redirect('login')