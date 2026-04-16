from django.urls import path
from django.contrib.auth import views as auth_views
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView)

from master_admin import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('quanLySuKien/', views.quan_ly_view, name='quanLySuKien'),
    path('quanLySuKienDaDienRa/', views.quan_ly_da_dien_ra_view, name='quanLySuKienDaDienRa'),
    path('quanLySuKienPhatSinh/', views.quan_ly_su_kien_phat_sinh_view, name='quanLySuKienPhatSinh'),
    path('duyetSuKien/', views.duyet_su_kien_view, name='duyetSuKien'),
    path('pheDuyetSuKien/<int:event_id>/', views.phe_duyet_su_kien_view, name='pheDuyetSuKien'),
    path('khongDuyetSuKien/<int:event_id>/', views.khong_duyet_su_kien_view, name='khongDuyetSuKien'),
    path('xoaSuKien/<int:event_id>/', views.xoa_su_kien_view, name='xoaSuKien'),
    path('quanLyDanhMuc/', views.quan_ly_danh_muc_view, name='quanLyDanhMuc'),
    path('xoaTieuChi/<int:id>/', views.xoa_tieu_chi, name='xoaTieuChi'),
    path('getCategories/', views.get_categories, name='get_categories_api'),
    path('quanLyNguoiDung/', views.quan_ly_nguoi_dung_view, name='quanLyNguoiDung'),
    path('xoaNguoiDung/<int:user_id>/', views.xoa_nguoi_dung_view, name='xoaNguoiDung'),
    path('login/', views.custom_login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # path('signup/', views.signup, name="signup")
]
