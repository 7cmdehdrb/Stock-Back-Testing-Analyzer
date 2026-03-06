import io
import os
import sqlite3
import traceback
import json
from datetime import datetime, timedelta
import hashlib
import hmac
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import numpy as np
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, url_for, session, redirect
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
import openai

# .env 파일 로드
load_dotenv()

# Flask 및 SQLAlchemy 설정
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(os.path.dirname(__file__), 'stock_cache.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# 세션 설정
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)  # 세션 유효기간 7일

# OpenAI API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# AI 분석 rate limiting과 캐싱을 위한 딕셔너리
# AI 분석 rate limiting과 캐싱을 위한 딕셔너리 (user_id 기반)
ai_analysis_cache = {}  # {user_id: {"timestamp": datetime, "result": dict}}
ai_analysis_rate_limit = {}  # {user_id: last_request_time}

# DB 파일 경로
DB_PATH = os.path.join(os.path.dirname(__file__), "stock_cache.db")

# 헤지펀드 벤치마크 매핑
HEDGEFUND_BENCHMARKS = {
    "HEDGEFUND_BLACKROCK": {
        "name": "블랙록 (BlackRock)",
        "csv_path": os.path.join(
            os.path.dirname(__file__), "sample_portfolio", "BLACKROCK.csv"
        ),
    },
    "HEDGEFUND_BERKSHIRE": {
        "name": "버크셔 해서웨이 (Berkshire Hathaway)",
        "csv_path": os.path.join(
            os.path.dirname(__file__), "sample_portfolio", "BERKSHIRE_HATHAWAY.csv"
        ),
    },
}

# SQLAlchemy 설정
db = SQLAlchemy(app)


# SQLAlchemy 모델 정의
class StockPriceCache(db.Model):
    __tablename__ = "stock_price_cache"

    ticker = db.Column(db.String(20), primary_key=True)
    date = db.Column(db.String(10), primary_key=True)
    close_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<StockPrice {self.ticker} {self.date}>"


class SavedPortfolio(db.Model):
    __tablename__ = "saved_portfolios"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )  # 기존 데이터 호환
    name = db.Column(db.String(200), nullable=False)
    csv_content = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.String(10))
    benchmark_ticker = db.Column(db.String(20))
    base_currency = db.Column(db.String(3))
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_accessed = db.Column(db.DateTime, default=datetime.now)

    # 관계 설정
    user = db.relationship("User", backref="portfolios")

    def __repr__(self):
        return f"<Portfolio {self.name}>"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(
        db.String(255), nullable=True
    )  # 소셜 로그인은 비밀번호 없음
    nickname = db.Column(db.String(100), unique=True, nullable=False)
    account_type = db.Column(
        db.String(20), nullable=False, default="local"
    )  # 'local', 'google', 'kakao'
    is_admin = db.Column(db.Boolean, default=False, nullable=False)  # 관리자 권한
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<User {self.email} ({self.account_type})>"


class EmailVerification(db.Model):
    __tablename__ = "email_verifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<EmailVerification {self.email}>"


class ExchangeRateCache(db.Model):
    """환율 데이터 캐시 (USD/KRW)"""

    __tablename__ = "exchange_rate_cache"

    date = db.Column(db.String(10), primary_key=True)  # YYYY-MM-DD
    open = db.Column(db.Float, nullable=False)
    high = db.Column(db.Float, nullable=False)
    low = db.Column(db.Float, nullable=False)
    close = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<ExchangeRate {self.date} {self.close}>"


# Flask-Admin ModelView 정의
class StockPriceCacheAdmin(ModelView):
    def is_accessible(self):
        """접근 권한 확인"""
        return session.get("admin_authenticated", False)

    def inaccessible_callback(self, name, **kwargs):
        """접근 불가능할 때 로그인 페이지로 리다이렉트"""
        return redirect(url_for("admin_login", next=request.url))

    column_list = ["ticker", "date", "close_price", "created_at"]
    column_searchable_list = ["ticker"]
    column_sortable_list = ["ticker", "date", "created_at"]
    column_default_sort = [("ticker", False), ("date", True)]
    page_size = 50
    can_export = True
    export_types = ["csv", "xlsx"]


class SavedPortfolioAdmin(ModelView):
    def is_accessible(self):
        """접근 권한 확인"""
        return session.get("admin_authenticated", False)

    def inaccessible_callback(self, name, **kwargs):
        """접근 불가능할 때 로그인 페이지로 리다이렉트"""
        return redirect(url_for("admin_login", next=request.url))

    column_list = [
        "id",
        "user_id",
        "name",
        "start_date",
        "benchmark_ticker",
        "base_currency",
        "created_at",
        "last_accessed",
    ]
    column_searchable_list = ["name", "benchmark_ticker"]
    column_sortable_list = ["id", "name", "created_at", "last_accessed"]
    column_default_sort = [("last_accessed", True)]
    page_size = 50
    can_export = True
    export_types = ["csv", "xlsx"]
    # CSV 내용은 리스트에서 제외 (너무 길어서)
    column_exclude_list = ["csv_content"]
    # 상세보기/수정에서는 표시
    form_excluded_columns = []


class UserAdmin(ModelView):
    def is_accessible(self):
        """접근 권한 확인"""
        return session.get("admin_authenticated", False)

    def inaccessible_callback(self, name, **kwargs):
        """접근 불가능할 때 로그인 페이지로 리다이렉트"""
        return redirect(url_for("admin_login", next=request.url))

    column_list = [
        "id",
        "email",
        "nickname",
        "account_type",
        "is_admin",
        "password_hash",
        "created_at",
        "last_login",
        "is_active",
    ]
    column_searchable_list = ["email", "nickname"]
    column_sortable_list = ["id", "email", "nickname", "created_at", "last_login"]
    column_default_sort = [("created_at", True)]
    column_filters = ["account_type", "is_active", "is_admin"]
    page_size = 50
    can_export = True
    export_types = ["csv", "xlsx"]
    # 모든 컬럼 표시 (숨김 없음)
    form_excluded_columns = []
    # 읽기 전용으로 표시 (포매터 제거)
    column_formatters = {}
    # 설명
    column_descriptions = {
        "account_type": "local: 로컬 가입, google: 구글, kakao: 카카오",
        "password_hash": "암호화된 비밀번호 (HMAC-SHA256)",
        "is_admin": "관리자 권한 여부",
    }
    # 상세보기에서 전체 표시
    column_details_list = [
        "id",
        "email",
        "nickname",
        "account_type",
        "is_admin",
        "password_hash",
        "created_at",
        "last_login",
        "is_active",
    ]


class EmailVerificationAdmin(ModelView):
    def is_accessible(self):
        """접근 권한 확인"""
        return session.get("admin_authenticated", False)

    def inaccessible_callback(self, name, **kwargs):
        """접근 불가능할 때 로그인 페이지로 리다이렉트"""
        return redirect(url_for("admin_login", next=request.url))

    column_list = ["id", "email", "code", "created_at", "expires_at", "is_verified"]
    column_searchable_list = ["email", "code"]
    column_sortable_list = ["id", "email", "created_at", "expires_at"]
    column_default_sort = [("created_at", True)]
    column_filters = ["is_verified"]
    page_size = 50
    can_export = True
    export_types = ["csv", "xlsx"]


class ExchangeRateCacheAdmin(ModelView):
    def is_accessible(self):
        """접근 권한 확인"""
        return session.get("admin_authenticated", False)

    def inaccessible_callback(self, name, **kwargs):
        """접근 불가능할 때 로그인 페이지로 리다이렉트"""
        return redirect(url_for("admin_login", next=request.url))

    column_list = ["date", "open", "high", "low", "close", "volume", "created_at"]
    column_searchable_list = ["date"]
    column_sortable_list = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "created_at",
    ]
    column_default_sort = [("date", True)]  # 날짜 내림차순
    column_filters = ["date"]
    page_size = 50
    can_export = True
    export_types = ["csv", "xlsx"]

    column_labels = {
        "date": "날짜",
        "open": "시가",
        "high": "고가",
        "low": "저가",
        "close": "종가",
        "volume": "거래량",
        "created_at": "생성일시",
    }

    column_formatters = {
        "open": lambda v, c, m, p: f"₩{m.open:.2f}",
        "high": lambda v, c, m, p: f"₩{m.high:.2f}",
        "low": lambda v, c, m, p: f"₩{m.low:.2f}",
        "close": lambda v, c, m, p: f"₩{m.close:.2f}",
        "volume": lambda v, c, m, p: f"{m.volume:,.0f}",
    }


class DashboardView(AdminIndexView):
    """커스텀 대시보드 with 비밀번호 인증"""

    def is_accessible(self):
        """접근 권한 확인 - 세션에 admin_authenticated가 있는지 체크"""
        return session.get("admin_authenticated", False)

    def inaccessible_callback(self, name, **kwargs):
        """접근 불가능할 때 로그인 페이지로 리다이렉트"""
        return redirect(url_for("admin_login", next=request.url))

    @expose("/")
    def index(self):
        """대시보드 메인 페이지"""
        # 통계 데이터 수집
        stats = self.get_statistics()
        recent_users = self.get_recent_users()
        recent_portfolios = self.get_recent_portfolios()
        user_type_stats = self.get_user_type_stats()

        return self.render(
            "admin/dashboard.html",
            stats=stats,
            recent_users=recent_users,
            recent_portfolios=recent_portfolios,
            user_type_stats=user_type_stats,
        )

    def get_statistics(self):
        """주요 통계 데이터"""
        try:
            # 총 회원 수
            total_users = User.query.count()

            # 오늘 가입한 회원
            today = datetime.now().date()
            today_users = User.query.filter(
                db.func.date(User.created_at) == today
            ).count()

            # 이번 주 가입한 회원
            week_ago = datetime.now() - timedelta(days=7)
            week_users = User.query.filter(User.created_at >= week_ago).count()

            # 총 포트폴리오 수
            total_portfolios = SavedPortfolio.query.count()

            # 오늘 생성된 포트폴리오
            today_portfolios = SavedPortfolio.query.filter(
                db.func.date(SavedPortfolio.created_at) == today
            ).count()

            # 캐시된 주가 데이터 (티커 수)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT ticker) FROM stock_price_cache")
            cached_tickers = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM stock_price_cache")
            cached_records = cursor.fetchone()[0]

            # 환율 캐시 데이터
            cursor.execute("SELECT COUNT(*) FROM exchange_rate_cache")
            exchange_rate_records = cursor.fetchone()[0]
            cursor.execute("SELECT MIN(date), MAX(date) FROM exchange_rate_cache")
            exchange_rate_range = cursor.fetchone()
            conn.close()

            return {
                "total_users": total_users,
                "today_users": today_users,
                "week_users": week_users,
                "total_portfolios": total_portfolios,
                "today_portfolios": today_portfolios,
                "cached_tickers": cached_tickers,
                "cached_records": cached_records,
                "exchange_rate_records": exchange_rate_records,
                "exchange_rate_start": (
                    exchange_rate_range[0] if exchange_rate_range[0] else "N/A"
                ),
                "exchange_rate_end": (
                    exchange_rate_range[1] if exchange_rate_range[1] else "N/A"
                ),
            }
        except Exception as e:
            app.logger.error(f"통계 데이터 수집 오류: {e}")
            return {
                "total_users": 0,
                "today_users": 0,
                "week_users": 0,
                "total_portfolios": 0,
                "today_portfolios": 0,
                "cached_tickers": 0,
                "cached_records": 0,
                "exchange_rate_records": 0,
                "exchange_rate_start": "N/A",
                "exchange_rate_end": "N/A",
            }

    def get_recent_users(self, limit=5):
        """최근 가입한 회원"""
        try:
            users = User.query.order_by(User.created_at.desc()).limit(limit).all()
            return [
                {
                    "id": u.id,
                    "email": u.email,
                    "nickname": u.nickname,
                    "account_type": u.account_type,
                    "created_at": u.created_at,
                }
                for u in users
            ]
        except Exception as e:
            app.logger.error(f"최근 회원 조회 오류: {e}")
            return []

    def get_recent_portfolios(self, limit=5):
        """최근 생성된 포트폴리오"""
        try:
            portfolios = (
                SavedPortfolio.query.order_by(SavedPortfolio.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "benchmark": p.benchmark_ticker,
                    "created_at": p.created_at,
                }
                for p in portfolios
            ]
        except Exception as e:
            app.logger.error(f"최근 포트폴리오 조회 오류: {e}")
            return []

    def get_user_type_stats(self):
        """회원 유형별 통계"""
        try:
            local_count = User.query.filter_by(account_type="local").count()
            google_count = User.query.filter_by(account_type="google").count()
            kakao_count = User.query.filter_by(account_type="kakao").count()

            return {
                "local": local_count,
                "google": google_count,
                "kakao": kakao_count,
            }
        except Exception as e:
            app.logger.error(f"회원 유형 통계 오류: {e}")
            return {"local": 0, "google": 0, "kakao": 0}


# Flask-Admin 초기화
admin = Admin(
    app,
    name="Portfolio Admin",
    template_mode="bootstrap3",
    index_view=DashboardView(name="Dashboard", url="/admin"),
)
admin.add_view(StockPriceCacheAdmin(StockPriceCache, db.session, name="Stock Prices"))
admin.add_view(SavedPortfolioAdmin(SavedPortfolio, db.session, name="Portfolios"))
admin.add_view(UserAdmin(User, db.session, name="Users"))
admin.add_view(
    EmailVerificationAdmin(EmailVerification, db.session, name="Email Verifications")
)
admin.add_view(
    ExchangeRateCacheAdmin(ExchangeRateCache, db.session, name="Exchange Rates")
)


def init_database():
    """데이터베이스 초기화 및 테이블 생성"""
    # SQLAlchemy로 테이블 생성 (이미 존재하면 무시)
    with app.app_context():
        db.create_all()


def hash_password(password: str) -> str:
    """비밀번호를 SHA256으로 해싱"""
    secret_key = app.config["SECRET_KEY"]
    if not secret_key:
        raise ValueError("SECRET_KEY가 설정되지 않았습니다.")

    # HMAC-SHA256 사용 (더 안전함)
    password_bytes = password.encode("utf-8")
    key_bytes = secret_key.encode("utf-8")
    hashed = hmac.new(key_bytes, password_bytes, hashlib.sha256)
    return hashed.hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """비밀번호 검증"""
    return hash_password(password) == password_hash


def generate_verification_code() -> str:
    """6자리 인증번호 생성"""
    return str(random.randint(100000, 999999))


def send_verification_email(email: str, code: str) -> bool:
    """이메일 인증번호 전송"""
    try:
        # 환경변수에서 이메일 설정 가져오기
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_PASSWORD")

        if not sender_email or not sender_password:
            app.logger.error("이메일 설정이 환경변수에 없습니다.")
            # 개발 모드에서는 콘솔에 출력
            print(f"📧 [개발 모드] 인증번호: {code} (이메일: {email})")
            return True  # 개발 모드에서는 성공으로 처리

        # 이메일 메시지 구성
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = email
        msg["Subject"] = "포트폴리오 분석기 - 이메일 인증번호"

        body = f"""
        안녕하세요, 포트폴리오 성과 분석기입니다.
        
        회원가입을 위한 인증번호는 다음과 같습니다:
        
        인증번호: {code}
        
        이 인증번호는 5분간 유효합니다.
        본인이 요청하지 않은 경우, 이 이메일을 무시해주세요.
        
        감사합니다.
        """

        msg.attach(MIMEText(body, "plain"))

        # SMTP 서버 연결 및 전송
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        app.logger.info(f"✅ 인증번호 이메일 전송 성공: {email}")
        return True

    except Exception as e:
        app.logger.error(f"❌ 이메일 전송 실패: {e}")
        # 개발 모드에서는 콘솔에 출력
        print(f"📧 [개발 모드] 인증번호: {code} (이메일: {email})")
        return True  # 개발 모드에서는 성공으로 처리


def get_cached_prices(ticker, start_date: pd.Timestamp, end_date: pd.Timestamp):
    """DB에서 캐시된 가격 데이터 조회"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        query = """
            SELECT date, close_price 
            FROM stock_price_cache 
            WHERE ticker = ? AND date >= ? AND date <= ?
            ORDER BY date
        """

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        cursor.execute(query, (ticker, start_str, end_str))
        results = cursor.fetchall()

        if not results:
            return None

        # DataFrame으로 변환
        df = pd.DataFrame(results, columns=["date", "close_price"])
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

        return df["close_price"]
    except Exception as e:
        return None
    finally:
        if conn:
            conn.close()


def save_prices_to_cache(ticker, price_series: pd.Series):
    """가격 데이터를 DB에 저장"""
    if price_series is None or len(price_series) == 0:
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # 데이터 준비 (NaN 값 제외)
        data_to_insert = []
        for date, price in price_series.items():
            # NaN 값 체크
            if pd.notna(price) and not np.isnan(price):
                date: pd.Timestamp

                date_str = date.strftime("%Y-%m-%d")
                data_to_insert.append((ticker, date_str, float(price)))

        if not data_to_insert:
            return

        # INSERT OR REPLACE로 중복 방지
        cursor.executemany(
            """
            INSERT OR REPLACE INTO stock_price_cache (ticker, date, close_price)
            VALUES (?, ?, ?)
            """,
            data_to_insert,
        )

        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def get_current_exchange_rate():
    """현재 USD/KRW 환율 가져오기"""
    try:
        # USDKRW=X 티커로 환율 정보 가져오기
        krw = yf.Ticker("USDKRW=X")
        data = krw.history(period="1d")
        if not data.empty:
            return data["Close"].iloc[-1]
        else:
            # 기본값 (최근 평균 환율)
            return 1350.0
    except Exception as e:
        return 1350.0


def get_stock_name(ticker):
    """티커로부터 종목명 가져오기

    Args:
        ticker: 주식 티커 심볼

    Returns:
        종목명 (가져오기 실패 시 티커 반환)
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # longName 우선, 없으면 shortName, 둘 다 없으면 티커 반환
        name = info.get("longName") or info.get("shortName") or ticker

        # 종목명이 너무 길면 shortName 사용
        if len(name) > 50 and info.get("shortName"):
            name = info.get("shortName")

        return name
    except Exception as e:
        app.logger.warning(f"⚠ Could not fetch name for {ticker}: {e}")
        return ticker


def fetch_stock_data(ticker, start_date, end_date, max_retries=3):
    """Yahoo Finance에서 주가 데이터 가져오기 (DB 캐시 활용)

    상장일이 start_date보다 늦은 경우에도 상장 이후 데이터를 반환하여
    fill_missing_dates에서 상장일 이전 구간을 상장 시 가격으로 채울 수 있도록 함

    Args:
        ticker: 티커 심볼
        start_date: 시작 날짜
        end_date: 종료 날짜
        max_retries: API 실패 시 최대 재시도 횟수 (기본값: 3)
    """
    import time

    try:
        # 1. 먼저 DB 캐시에서 데이터 조회
        cached_data = get_cached_prices(ticker, start_date, end_date)

        # 2. 캐시에 모든 데이터가 있는지 확인
        if cached_data is not None and len(cached_data) > 0:
            # 날짜 범위 확인
            expected_start = pd.to_datetime(start_date)
            expected_end = pd.to_datetime(end_date)
            cached_start = cached_data.index.min()
            cached_end = cached_data.index.max()

            # 캐시가 요청 범위를 모두 커버하는지 확인 (±7일 허용)
            # 시작일과 종료일 모두 확인해야 함
            start_covered = cached_start <= expected_start + timedelta(days=7)
            end_covered = cached_end >= expected_end - timedelta(days=7)

            if start_covered and end_covered:
                # 캐시가 요청 범위를 완전히 커버하는 경우
                app.logger.info(
                    f"✓ Using cached data for {ticker} "
                    f"(cached: {cached_start.date()} ~ {cached_end.date()}, "
                    f"requested: {expected_start.date()} ~ {expected_end.date()})"
                )
                return cached_data
            else:
                # 캐시가 불완전한 경우 - API에서 다시 가져와야 함
                app.logger.info(
                    f"⚠ Cache incomplete for {ticker}: "
                    f"cached={cached_start.date()}~{cached_end.date()}, "
                    f"requested={expected_start.date()}~{expected_end.date()}, "
                    f"start_covered={start_covered}, end_covered={end_covered}"
                )
                # 캐시를 사용하지 않고 API로 새로 가져옴

        # 3. 캐시에 없으면 Yahoo Finance에서 가져오기 (재시도 로직 추가)
        data = None
        last_error = None

        for attempt in range(max_retries):
            try:
                stock = yf.Ticker(ticker)
                data = stock.history(start=start_date, end=end_date)

                # 데이터가 성공적으로 가져와졌으면 재시도 루프 종료
                if not data.empty or attempt == max_retries - 1:
                    break

            except Exception as e:
                last_error = e
                app.logger.warning(
                    f"⚠ Attempt {attempt + 1}/{max_retries} failed for {ticker}: {e}"
                )

                # 마지막 시도가 아니면 잠시 대기 후 재시도
                if attempt < max_retries - 1:
                    time.sleep(1)  # 1초 대기
                    continue
                else:
                    # 마지막 시도도 실패
                    break

        # 데이터가 비어있는 경우 (상장일이 늦을 수 있음)
        if data is None or data.empty:
            # 더 넓은 범위로 다시 시도 (최근 5년 또는 상장일부터)
            app.logger.warning(
                f"⚠ No data for {ticker} in requested range, trying broader range..."
            )

            for attempt in range(max_retries):
                try:
                    stock = yf.Ticker(ticker)
                    data = stock.history(period="5y")

                    if not data.empty or attempt == max_retries - 1:
                        break

                except Exception as e:
                    last_error = e
                    app.logger.warning(
                        f"⚠ Broad range attempt {attempt + 1}/{max_retries} failed for {ticker}: {e}"
                    )

                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    else:
                        break

            if data is None or data.empty:
                if last_error:
                    app.logger.warning(
                        f"❌ {ticker}: Failed after {max_retries} attempts. Last error: {last_error}"
                    )
                else:
                    app.logger.warning(
                        f"❌ {ticker}: No data available (symbol may be delisted)"
                    )
                return None
            else:
                # 상장일 이후 데이터가 있음
                listing_date: pd.Timestamp = data.index.min()
                app.logger.info(
                    f"  ℹ {ticker} listing date appears to be around {listing_date.date()}"
                )

        price_data = data["Close"]

        # timezone 제거 (캐시된 데이터와 일관성 유지)
        if hasattr(price_data.index, "tz") and price_data.index.tz is not None:
            price_data.index = price_data.index.tz_localize(None)

        # NaN 값 제거
        price_data = price_data.dropna()

        if len(price_data) == 0:
            app.logger.warning(f"❌ {ticker}: No valid price data after cleaning")
            return None

        # 4. 새로 가져온 데이터를 DB에 저장
        save_prices_to_cache(ticker, price_data)
        app.logger.info(
            f"✓ Successfully fetched and cached {len(price_data)} data points for {ticker}"
        )

        return price_data

    except Exception as e:
        app.logger.warning(f"❌ Unexpected error fetching {ticker}: {e}")
        import traceback

        app.logger.warning(traceback.format_exc())
        return None


def normalize_ticker(ticker, country):
    """티커 정규화 (한국 종목에 .KS 자동 추가)

    한국 주식 티커는 6자리 숫자이므로, 앞의 0이 제거되지 않도록 처리
    """
    ticker = str(ticker).strip()

    # 한국 종목인 경우
    if country == "한국":
        # 이미 .KS나 .KQ가 붙어있는 경우 그대로 반환
        if ticker.endswith(".KS") or ticker.endswith(".KQ"):
            # 티커 부분만 추출해서 6자리로 패딩
            ticker_code = ticker.split(".")[0]
            suffix = ticker.split(".")[1]
            if ticker_code.isdigit():
                ticker_code = ticker_code.zfill(6)  # 6자리로 패딩
            return f"{ticker_code}.{suffix}"

        # 숫자로만 이루어진 경우 (예: 005930 또는 5930)
        if ticker.isdigit():
            # 한국 주식 티커는 6자리이므로 앞에 0을 채워줌
            ticker = ticker.zfill(6)
            ticker = f"{ticker}.KS"
            return ticker

        # 숫자가 아니지만 .KS/.KQ가 없는 경우 (잘못된 입력)
        # 기본적으로 .KS 추가
        ticker = f"{ticker}.KS"
        return ticker

    return ticker


def merge_duplicate_tickers(portfolio_df: pd.DataFrame) -> pd.DataFrame:
    """동일 티커를 가진 종목의 보유량을 합산"""
    # 필수 컬럼 확인
    if "티커" not in portfolio_df.columns or "보유량" not in portfolio_df.columns:
        return portfolio_df

    # 티커 정규화 (한국 종목에 .KS 추가)
    if "국가" in portfolio_df.columns:
        portfolio_df["티커"] = portfolio_df.apply(
            lambda row: normalize_ticker(row["티커"], row.get("국가", "")), axis=1
        )

    # 티커별로 그룹화하여 보유량 합산
    # 첫 번째 행의 다른 정보(종목명, 국가, 분류 등)는 유지
    grouped = portfolio_df.groupby("티커", as_index=False).agg(
        {
            "보유량": "sum",  # 보유량은 합산
            **{
                col: "first"
                for col in portfolio_df.columns
                if col not in ["티커", "보유량"]
            },
        }
    )

    return grouped


def fill_missing_dates(price_series, start_date, end_date):
    """휴장일 및 상장일로 인한 빈 데이터 처리

    Args:
        price_series: 주가 시계열 데이터
        start_date: 분석 시작 날짜
        end_date: 분석 종료 날짜

    Returns:
        보간된 주가 시계열 데이터
    """
    if price_series is None or len(price_series) == 0:
        app.logger.warning("⚠ fill_missing_dates: No data provided")
        return None

    try:
        # 원본 데이터의 인덱스를 timezone-naive로 변환
        if hasattr(price_series.index, "tz") and price_series.index.tz is not None:
            price_series.index = price_series.index.tz_localize(None)

        # 인덱스가 DatetimeIndex인지 확인
        if not isinstance(price_series.index, pd.DatetimeIndex):
            price_series.index = pd.to_datetime(price_series.index)

        # start_date, end_date도 timezone-naive로 변환
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        if hasattr(start_date, "tz") and start_date.tz is not None:
            start_date = start_date.tz_localize(None)
        if hasattr(end_date, "tz") and end_date.tz is not None:
            end_date = end_date.tz_localize(None)

        # 데이터의 실제 시작일 (상장일)
        actual_start = price_series.index.min()

        # 만약 상장일이 분석 시작일보다 나중이면, 상장일을 새로운 시작일로 사용
        effective_start = max(start_date, actual_start)

        app.logger.info(
            f"📅 fill_missing_dates: requested={start_date.date()}, actual={actual_start.date()}, effective={effective_start.date()}"
        )

        # 전체 날짜 범위 생성 (요청 시작일부터 종료일까지 모든 날짜 포함)
        all_dates = pd.date_range(start=start_date, end=end_date, freq="D")

        # 기존 데이터를 전체 날짜 범위로 확장
        price_series_filled = price_series.reindex(all_dates)

        # 데이터가 있는 첫 날짜 확인 (상장일)
        first_valid_date = price_series_filled.first_valid_index()

        if first_valid_date is None:
            # 유효한 데이터가 하나도 없음
            app.logger.warning("⚠ fill_missing_dates: No valid data after reindexing")
            return price_series

        # 상장일의 첫 가격
        first_price = price_series_filled[first_valid_date]

        # 상장 이전 날짜가 있는 경우: 상장 첫날 가격으로 채움 (backward fill)
        if first_valid_date > all_dates[0]:
            app.logger.info(
                f"  📌 Filling pre-listing dates with first price: {first_price:.2f}"
            )
            price_series_filled.loc[:first_valid_date] = first_price

        # 상장 이후 빈 데이터 (휴장일 등): 선형 보간
        # interpolate는 NaN 사이의 값만 채우므로 먼저 실행
        price_series_filled = price_series_filled.interpolate(
            method="linear", limit_direction="forward"
        )

        # 아직도 빈 값이 있다면 (데이터 끝 부분) forward fill
        if price_series_filled.isna().any():
            price_series_filled = price_series_filled.ffill()

        # 그래도 남아있는 NaN은 backward fill (데이터 시작 부분)
        if price_series_filled.isna().any():
            price_series_filled = price_series_filled.bfill()

        # 최종 확인
        if price_series_filled.isna().any():
            nan_count = price_series_filled.isna().sum()
            app.logger.warning(
                f"⚠ Still {nan_count} NaN values after fill_missing_dates"
            )

        filled_count = len(all_dates) - len(price_series)
        app.logger.info(f"  ✓ Filled {filled_count} missing dates")

        return price_series_filled

    except Exception as e:
        app.logger.error(f"❌ Error in fill_missing_dates: {e}")
        import traceback

        app.logger.error(traceback.format_exc())
        # 오류 시 원본 데이터 반환
        return price_series


def calculate_portfolio_returns_with_dca(
    portfolio_df: pd.DataFrame,
    dca_data: list,
    start_date: pd.Timestamp,
    base_currency="USD",
):
    """DCA(적립식 투자)가 포함된 포트폴리오 수익률 계산

    각 투자 시점의 가격으로 주식을 매수하는 시뮬레이션을 수행합니다.
    """
    end_date = datetime.now()
    exchange_rate = get_current_exchange_rate()

    app.logger.info(f"📈 Calculating portfolio with DCA simulation")
    app.logger.info(f"   Period: {start_date.date()} to {end_date.date()}")

    # 날짜 범위 생성
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    # 초기 포트폴리오 처리
    portfolio_value_series = pd.Series(0.0, index=date_range)
    total_initial_value = 0
    total_initial_value_with_cash = 0
    cash_holdings = {}
    failed_tickers = []
    portfolio_data = {}

    # 1. 초기 보유 종목 처리 (DCA 아닌 일반 보유)
    for _, row in portfolio_df.iterrows():
        ticker = row["티커"]
        quantity = row["보유량"]
        country = row.get("국가", "미국")
        asset_class = row.get("분류", "")

        if asset_class == "현금":
            if country == "한국" and base_currency == "USD":
                cash_value = quantity / exchange_rate
            elif country == "미국" and base_currency == "KRW":
                cash_value = quantity * exchange_rate
            else:
                cash_value = quantity

            cash_holdings[ticker] = {
                "value": cash_value,
                "country": country,
                "ticker": ticker,
            }
            total_initial_value_with_cash += cash_value
            continue

        # 주가 데이터 가져오기
        price_data = fetch_stock_data(ticker, start_date, end_date)
        if price_data is None or len(price_data) == 0:
            app.logger.warning(f"⚠ Skipping {ticker}: No price data")
            failed_tickers.append(ticker)
            continue

        stock_name = row.get("종목명")
        if not stock_name or pd.isna(stock_name):
            stock_name = get_stock_name(ticker)

        price_data = fill_missing_dates(price_data, start_date, end_date)
        if price_data is None or len(price_data) == 0:
            failed_tickers.append(ticker)
            continue

        # 환율 적용
        if base_currency == "USD" and country == "한국":
            price_data = price_data / exchange_rate
        elif base_currency == "KRW" and country == "미국":
            price_data = price_data * exchange_rate

        # 초기 보유 종목의 가치 변화를 시리즈에 추가
        stock_value_series = price_data * quantity
        portfolio_value_series += stock_value_series.reindex(date_range, method="ffill")

        initial_price = price_data.iloc[0]
        initial_value = initial_price * quantity
        total_initial_value += initial_value
        total_initial_value_with_cash += initial_value

        portfolio_data[ticker] = {
            "prices": price_data,
            "quantity": quantity,
            "initial_value": initial_value,
            "name": stock_name,
            "country": country,
        }

    # 2. DCA 투자 시뮬레이션
    # DCA의 경우 누적 투자 금액도 시계열로 추적해야 함
    cumulative_invested_series = pd.Series(0.0, index=date_range)

    # 초기 보유 자산의 투자액을 시작부터 추가
    if total_initial_value_with_cash > 0:
        cumulative_invested_series += total_initial_value_with_cash

    has_dca = False

    for dca_item in dca_data:
        ticker = dca_item["ticker"]
        quantity_per_period = dca_item["quantity"]
        country = dca_item["country"]
        frequency = dca_item["frequency"]

        normalized_ticker = normalize_ticker(ticker, country)

        app.logger.info(
            f"  📊 Simulating DCA: {normalized_ticker} - {quantity_per_period} shares per {frequency}"
        )

        # 주가 데이터 가져오기
        price_data = fetch_stock_data(normalized_ticker, start_date, end_date)
        if price_data is None or len(price_data) == 0:
            app.logger.warning(f"⚠ Skipping DCA for {normalized_ticker}: No price data")
            failed_tickers.append(normalized_ticker)
            continue

        stock_name = get_stock_name(normalized_ticker)
        price_data = fill_missing_dates(price_data, start_date, end_date)

        if price_data is None or len(price_data) == 0:
            failed_tickers.append(normalized_ticker)
            continue

        # 환율 적용
        if base_currency == "USD" and country == "한국":
            price_data = price_data / exchange_rate
        elif base_currency == "KRW" and country == "미국":
            price_data = price_data * exchange_rate

        # 투자 일정 생성
        if frequency == "weekly":
            investment_dates = pd.date_range(
                start=start_date, end=end_date, freq="W-MON"
            )
        elif frequency == "monthly":
            investment_dates = pd.date_range(start=start_date, end=end_date, freq="MS")
        elif frequency == "quarterly":
            investment_dates = pd.date_range(start=start_date, end=end_date, freq="QS")
        else:
            investment_dates = pd.date_range(start=start_date, end=end_date, freq="MS")

        # DCA 시뮬레이션: 각 투자 시점부터 현재까지의 가치 계산
        # 각 날짜별 누적 보유 수량 추적
        accumulated_shares_series = pd.Series(0.0, index=date_range)
        total_invested_amount = 0
        total_shares_accumulated = 0

        has_dca = True  # DCA가 있음을 표시

        for invest_date in investment_dates:
            # 투자 날짜가 가격 데이터 범위 내에 있는지 확인
            if invest_date not in price_data.index:
                # 가장 가까운 다음 거래일 찾기
                future_dates = price_data.index[price_data.index >= invest_date]
                if len(future_dates) == 0:
                    continue
                invest_date = future_dates[0]

            # 투자 시점의 가격으로 매수
            purchase_price = price_data.loc[invest_date]
            invested_amount = purchase_price * quantity_per_period
            total_invested_amount += invested_amount
            total_shares_accumulated += quantity_per_period

            # 이 투자 시점 이후의 모든 날짜에 보유 수량 증가
            future_dates_mask = date_range >= invest_date
            accumulated_shares_series[future_dates_mask] += quantity_per_period

            # 누적 투자 금액도 시계열로 추적 (투자 시점 이후 증가)
            cumulative_invested_series[future_dates_mask] += invested_amount

        # 각 날짜의 가치 = 그 시점까지 누적된 주식 수 × 현재 가격
        price_series_aligned = price_data.reindex(date_range, method="ffill")
        dca_value_series = accumulated_shares_series * price_series_aligned

        # 전체 포트폴리오에 DCA 가치 추가
        portfolio_value_series += dca_value_series

        app.logger.info(
            f"    ✓ DCA simulation: {len(investment_dates)} investments, {total_shares_accumulated} shares, total invested: {total_invested_amount:.2f}"
        )

        # 총 투자 금액을 초기 가치에 추가 (모든 투자 금액의 합)
        total_initial_value += total_invested_amount
        total_initial_value_with_cash += total_invested_amount

        # DCA 종목을 기존 보유에 병합 (별도로 표시하지 않음)
        if normalized_ticker in portfolio_data:
            # 이미 있는 종목: 수량과 초기 가치 합산
            portfolio_data[normalized_ticker]["quantity"] += total_shares_accumulated
            portfolio_data[normalized_ticker]["initial_value"] += total_invested_amount
            app.logger.info(
                f"    ✓ Merged with existing position: {portfolio_data[normalized_ticker]['quantity']} total shares"
            )
        else:
            # 새로운 종목: 추가
            portfolio_data[normalized_ticker] = {
                "prices": price_data,
                "quantity": total_shares_accumulated,
                "initial_value": total_invested_amount,
                "name": stock_name,
                "country": country,
            }
            app.logger.info(
                f"    ✓ Added as new position: {total_shares_accumulated} shares"
            )

    # 수익률 계산
    if has_dca:
        # DCA가 있는 경우: 정규화된 포트폴리오 시리즈 사용
        # 각 시점의 "투자 대비 가치 비율"을 계산하여 일반 수익률처럼 사용
        # 0으로 나누기 방지
        safe_invested = cumulative_invested_series.replace(0, 1e-10)

        # 정규화된 포트폴리오 시리즈 = 가치 / 누적 투자액
        # 이렇게 하면 "1.0 = 본전, 1.1 = 10% 수익" 형태가 됨
        normalized_portfolio = portfolio_value_series / safe_invested

        # 이제 일반적인 pct_change() 사용 가능
        portfolio_returns = normalized_portfolio.pct_change().dropna()

        app.logger.info(f"✓ DCA mode: Using normalized returns")
        app.logger.info(f"  Initial invested: {cumulative_invested_series.iloc[0]:.2f}")
        app.logger.info(f"  Final invested: {cumulative_invested_series.iloc[-1]:.2f}")
        app.logger.info(f"  Final value: {portfolio_value_series.iloc[-1]:.2f}")
        app.logger.info(f"  Final normalized: {normalized_portfolio.iloc[-1]:.4f}")
    else:
        # DCA가 없는 경우: 기존 방식 (일별 가격 변화율)
        portfolio_returns = portfolio_value_series.pct_change().dropna()
        app.logger.info(f"✓ Standard mode: Using daily price change returns")

    app.logger.info(
        f"✓ Portfolio calculation complete: {len(portfolio_data)} positions"
    )

    return (
        portfolio_returns,
        portfolio_value_series,
        portfolio_data,
        cash_holdings,
        total_initial_value_with_cash,
        failed_tickers,
        has_dca,  # DCA 사용 여부 반환
    )


def apply_dca_to_portfolio(
    portfolio_df: pd.DataFrame,
    dca_data: list,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
):
    """적립식 투자(DCA)를 포트폴리오에 적용

    Args:
        portfolio_df: 초기 포트폴리오 DataFrame
        dca_data: 적립식 투자 정보 리스트 [{'ticker': 'AAPL', 'quantity': 1, 'country': '미국', 'frequency': 'monthly'}]
        start_date: 시작 날짜
        end_date: 종료 날짜

    Returns:
        최종 포트폴리오 DataFrame (누적된 수량으로 업데이트됨)
    """
    if not dca_data or len(dca_data) == 0:
        return portfolio_df

    app.logger.info(f"📈 Applying DCA investments: {len(dca_data)} items")

    # 날짜 범위 생성
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    # DCA 투자 일정 계산
    for dca_item in dca_data:
        ticker = dca_item["ticker"]
        quantity_per_period = dca_item["quantity"]
        country = dca_item["country"]
        frequency = dca_item["frequency"]

        # 티커 정규화
        normalized_ticker = normalize_ticker(ticker, country)

        app.logger.info(
            f"  📊 DCA: {normalized_ticker} - {quantity_per_period} shares per {frequency}"
        )

        # 투자 주기에 따라 날짜 생성
        if frequency == "weekly":
            investment_dates = pd.date_range(
                start=start_date, end=end_date, freq="W-MON"
            )
        elif frequency == "monthly":
            investment_dates = pd.date_range(
                start=start_date, end=end_date, freq="MS"
            )  # Month Start
        elif frequency == "quarterly":
            investment_dates = pd.date_range(
                start=start_date, end=end_date, freq="QS"
            )  # Quarter Start
        else:
            app.logger.warning(
                f"  ⚠️ Unknown frequency: {frequency}, defaulting to monthly"
            )
            investment_dates = pd.date_range(start=start_date, end=end_date, freq="MS")

        # 총 투자 횟수
        num_investments = len(investment_dates)
        total_quantity = quantity_per_period * num_investments

        app.logger.info(
            f"    ✓ Total investments: {num_investments} times = {total_quantity} shares"
        )

        # 포트폴리오에 해당 티커가 이미 있는지 확인
        existing_row = portfolio_df[portfolio_df["티커"] == normalized_ticker]

        if not existing_row.empty:
            # 기존 수량에 DCA 수량 추가
            idx = existing_row.index[0]
            original_quantity = portfolio_df.at[idx, "보유량"]
            portfolio_df.at[idx, "보유량"] = original_quantity + total_quantity
            app.logger.info(
                f"    ✓ Updated existing position: {original_quantity} + {total_quantity} = {original_quantity + total_quantity}"
            )
        else:
            # 새로운 행 추가
            new_row = pd.DataFrame(
                {
                    "티커": [normalized_ticker],
                    "보유량": [total_quantity],
                    "국가": [country],
                    "분류": ["주식"],
                }
            )
            portfolio_df = pd.concat([portfolio_df, new_row], ignore_index=True)
            app.logger.info(f"    ✓ Added new position: {total_quantity} shares")

    return portfolio_df


def calculate_portfolio_returns(
    portfolio_df: pd.DataFrame, start_date: pd.Timestamp, base_currency="USD"
):
    """포트폴리오 수익률 계산 (기준 통화 적용, 현금 제외)"""
    end_date = datetime.now()

    # 현재 환율 가져오기
    exchange_rate = get_current_exchange_rate()
    print(f"Current USD/KRW exchange rate: {exchange_rate}")

    # 각 종목의 수익률 데이터 수집
    portfolio_data = {}
    cash_holdings = {}
    failed_tickers = []  # 실패한 티커 추적
    total_initial_value = 0
    total_initial_value_with_cash = 0

    for _, row in portfolio_df.iterrows():
        ticker = row["티커"]
        quantity = row["보유량"]
        country = row.get("국가", "미국")  # 기본값은 미국
        asset_class = row.get("분류", "")

        # 현금인 경우 별도 처리
        if asset_class == "현금":
            # 현금 가치 계산 (환율 적용)
            if country == "한국" and base_currency == "USD":
                cash_value = quantity / exchange_rate
            elif country == "미국" and base_currency == "KRW":
                cash_value = quantity * exchange_rate
            else:
                cash_value = quantity

            cash_holdings[ticker] = {
                "value": cash_value,
                "country": country,
                "ticker": ticker,
            }
            total_initial_value_with_cash += cash_value
            continue

        # 주가 데이터 가져오기
        price_data = fetch_stock_data(ticker, start_date, end_date)

        if price_data is None or len(price_data) == 0:
            app.logger.warning(f"⚠ Skipping {ticker}: No price data available")
            failed_tickers.append(ticker)  # 실패한 티커 기록
            continue

        # 종목명 가져오기 (CSV에 있으면 사용, 없으면 API로 조회)
        stock_name = row.get("종목명")
        if not stock_name or pd.isna(stock_name):
            stock_name = get_stock_name(ticker)
            app.logger.info(f"📝 Fetched stock name for {ticker}: {stock_name}")

        # fill_missing_dates를 호출하여 상장일 이전 데이터를 상장 시 가격으로 채움
        app.logger.info(f"🔄 Filling missing dates for {ticker}...")
        price_data = fill_missing_dates(price_data, start_date, end_date)

        if price_data is None or len(price_data) == 0:
            app.logger.warning(f"⚠ Skipping {ticker}: Failed to process price data")
            failed_tickers.append(ticker)
            continue

        # 환율 적용
        # 기준 통화가 USD이고 한국 주식인 경우 -> USD로 환산
        # 기준 통화가 KRW이고 미국 주식인 경우 -> KRW로 환산
        if base_currency == "USD" and country == "한국":
            # 한국 주식을 USD로 환산 (KRW / 환율)
            price_data = price_data / exchange_rate
        elif base_currency == "KRW" and country == "미국":
            # 미국 주식을 KRW로 환산 (USD * 환율)
            price_data = price_data * exchange_rate

        initial_price = price_data.iloc[0]
        initial_value = initial_price * quantity
        total_initial_value += initial_value
        total_initial_value_with_cash += initial_value

        portfolio_data[ticker] = {
            "prices": price_data,
            "quantity": quantity,
            "initial_value": initial_value,
            "country": country,
            "asset_class": asset_class,
            "name": stock_name,  # CSV의 종목명 또는 API로 조회한 종목명
        }

    if not portfolio_data:
        app.logger.warning(
            f"❌ No valid portfolio data found. Cash holdings: {len(cash_holdings)}"
        )
        return (
            None,
            None,
            None,
            cash_holdings,
            total_initial_value_with_cash,
            failed_tickers,
            False,  # has_dca = False
        )

    # 모든 날짜의 합집합 구하기 (start_date 이후만)
    all_dates = pd.DatetimeIndex([])

    # start_date를 timezone-naive로 변환 (fetch_stock_data가 timezone 없는 데이터 반환)
    start_date_tz = pd.to_datetime(start_date)

    for data in portfolio_data.values():
        prices_index = data["prices"].index

        # start_date 이후 데이터만 사용
        ticker_dates = prices_index[prices_index >= start_date_tz]
        all_dates = all_dates.union(ticker_dates)

    all_dates = sorted(all_dates)

    # 포트폴리오 전체 가치 계산
    portfolio_values = []

    for date in all_dates:
        daily_value = 0
        for ticker, data in portfolio_data.items():
            # 해당 날짜의 가격 (없으면 forward fill)
            if date in data["prices"].index:
                price = data["prices"][date]
            else:
                # 가장 최근 가격 사용
                available_prices = data["prices"][data["prices"].index <= date]
                if len(available_prices) > 0:
                    price = available_prices.iloc[-1]
                else:
                    price = data["prices"].iloc[0]

            daily_value += price * data["quantity"]

        portfolio_values.append(daily_value)

    portfolio_series = pd.Series(portfolio_values, index=all_dates)

    # 일일 수익률 계산
    returns = portfolio_series.pct_change().dropna()

    # 포트폴리오 데이터와 현금 보유 정보 반환
    return (
        returns,
        portfolio_series,
        portfolio_data,
        cash_holdings,
        total_initial_value_with_cash,
        failed_tickers,  # 실패한 티커 리스트 반환
        False,  # has_dca = False (일반 포트폴리오)
    )


def calculate_weighted_annual_return(portfolio_returns: dict):
    """연 평균 수익률 계산 (영업일 가중평균)"""
    if len(portfolio_returns) == 0:
        return 0

    # 날짜를 연도별로 그룹화
    returns_by_year: dict[int, list[float]] = {}

    for date, ret in portfolio_returns.items():
        year = date.year
        if year not in returns_by_year:
            returns_by_year[year] = []
        returns_by_year[year].append(ret)

    # 각 연도의 수익률과 영업일 수 계산
    yearly_data = []
    for year, returns_list in returns_by_year.items():
        trading_days = len(returns_list)
        # 해당 연도의 누적 수익률
        year_cumulative = (1 + pd.Series(returns_list)).prod() - 1
        # 연율화 (해당 연도의 일부만 있는 경우 보정)
        year_return = (
            ((1 + year_cumulative) ** (252 / trading_days) - 1)
            if trading_days > 0
            else 0
        )
        yearly_data.append(
            {"year": year, "return": year_return, "trading_days": trading_days}
        )

    # 영업일 가중 평균
    total_trading_days = sum(d["trading_days"] for d in yearly_data)
    if total_trading_days == 0:
        return 0

    weighted_return = (
        sum(d["return"] * d["trading_days"] for d in yearly_data) / total_trading_days
    )

    # for d in yearly_data:
    #     weight = d["trading_days"] / total_trading_days * 100

    return weighted_return


def calculate_hedgefund_benchmark_returns(
    hedgefund_key: str, start_date: pd.Timestamp, base_currency: str
):
    """헤지펀드 포트폴리오를 벤치마크로 사용하기 위한 수익률 계산

    Args:
        hedgefund_key: HEDGEFUND_BLACKROCK 또는 HEDGEFUND_BERKSHIRE 등
        start_date: 분석 시작 날짜
        base_currency: 기준 통화 (USD 또는 KRW)

    Returns:
        pd.Series: 헤지펀드 포트폴리오의 일일 수익률
    """
    if hedgefund_key not in HEDGEFUND_BENCHMARKS:
        raise ValueError(f"알 수 없는 헤지펀드 벤치마크: {hedgefund_key}")

    hedgefund_info = HEDGEFUND_BENCHMARKS[hedgefund_key]
    csv_path = hedgefund_info["csv_path"]

    app.logger.info(f"📊 헤지펀드 벤치마크 로드: {hedgefund_info['name']}")
    app.logger.info(f"📁 CSV 경로: {csv_path}")

    # CSV 파일 읽기
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"헤지펀드 CSV 파일을 찾을 수 없습니다: {csv_path}")

    hedgefund_df = pd.read_csv(csv_path)

    # 필수 컬럼 확인
    required_columns = ["티커", "보유량", "국가", "분류"]
    missing_columns = [
        col for col in required_columns if col not in hedgefund_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f'헤지펀드 CSV 파일에 다음 컬럼이 필요합니다: {", ".join(missing_columns)}'
        )

    # 동일 티커 병합
    hedgefund_df = merge_duplicate_tickers(hedgefund_df)

    # 포트폴리오 수익률 계산
    result = calculate_portfolio_returns(hedgefund_df, start_date, base_currency)

    if result is None or result[0] is None:
        failed_tickers = result[5] if result and len(result) > 5 else []
        error_msg = f"헤지펀드 벤치마크 데이터를 가져올 수 없습니다."
        if failed_tickers:
            error_msg += f" 실패한 티커: {', '.join(failed_tickers)}"
        raise ValueError(error_msg)

    hedgefund_returns = result[0]  # 일일 수익률

    app.logger.info(
        f"✅ 헤지펀드 벤치마크 계산 완료: {len(hedgefund_returns)} 데이터 포인트"
    )

    return hedgefund_returns


def calculate_metrics(portfolio_returns: pd.Series, benchmark_returns: pd.Series):
    """샤프비, 소티노비, 알파, 베타, 평균 연 수익률 계산"""

    # 인덱스 정보 출력
    app.logger.info(f"\n🔍 Index comparison:")
    app.logger.info(f"Portfolio index type: {type(portfolio_returns.index)}")
    app.logger.info(
        f"Portfolio index tz: {getattr(portfolio_returns.index, 'tz', 'N/A')}"
    )
    app.logger.info(f"Portfolio first date: {portfolio_returns.index[0]}")
    app.logger.info(f"Benchmark index type: {type(benchmark_returns.index)}")
    app.logger.info(
        f"Benchmark index tz: {getattr(benchmark_returns.index, 'tz', 'N/A')}"
    )
    app.logger.info(f"Benchmark first date: {benchmark_returns.index[0]}")

    # timezone 통일
    if (
        hasattr(portfolio_returns.index, "tz")
        and portfolio_returns.index.tz is not None
    ):
        portfolio_returns.index = portfolio_returns.index.tz_localize(None)

    if (
        hasattr(benchmark_returns.index, "tz")
        and benchmark_returns.index.tz is not None
    ):
        benchmark_returns.index = benchmark_returns.index.tz_localize(None)

    # 공통 날짜만 사용
    common_dates = portfolio_returns.index.intersection(benchmark_returns.index)

    portfolio_returns = portfolio_returns[common_dates]
    benchmark_returns = benchmark_returns[common_dates]

    if len(portfolio_returns) == 0:
        app.logger.warning(f"❌ No common dates found!")
        return None

    # 수익률 차이 확인
    # returns_diff = (portfolio_returns - benchmark_returns).abs().mean()

    # 샘플 비교
    # for i in range(min(5, len(common_dates))):
    #     date = common_dates[i]

    # 연간화 계산을 위한 거래일 수
    trading_days = 252

    # 평균 연 수익률
    avg_return = portfolio_returns.mean() * trading_days

    # 표준편차 (연간화)
    std_dev = portfolio_returns.std() * np.sqrt(trading_days)

    # 샤프 비율 (무위험 수익률 0으로 가정)
    sharpe_ratio = avg_return / std_dev if std_dev != 0 else 0

    # app.logger.info(f"\n  📈 Sharpe Calculation:")
    # app.logger.info(f"Annualized return: {avg_return * 100:.2f}%")
    # app.logger.info(f"Annualized volatility: {std_dev * 100:.2f}%")
    # app.logger.info(f"Sharpe ratio: {sharpe_ratio:.4f}")

    # 소티노 비율 (하방 표준편차)
    downside_returns = portfolio_returns[portfolio_returns < 0]
    downside_std = downside_returns.std() * np.sqrt(trading_days)
    sortino_ratio = avg_return / downside_std if downside_std != 0 else 0

    # app.logger.info(f"\n  📉 Sortino Calculation:")
    # app.logger.info(
    #     f"    Downside returns count: {len(downside_returns)}/{len(portfolio_returns)}"
    # )
    # app.logger.info(f"Downside volatility: {downside_std * 100:.2f}%")
    # app.logger.info(f"Sortino ratio: {sortino_ratio:.4f}")

    # 베타 계산 수정 - 공분산과 분산 모두 일일 수익률 기준
    covariance = portfolio_returns.cov(benchmark_returns)
    benchmark_variance = benchmark_returns.var()
    beta = covariance / benchmark_variance if benchmark_variance != 0 else 0

    # app.logger.info(f"Covariance: {covariance:.6f}")
    # app.logger.info(f"Benchmark variance: {benchmark_variance:.6f}")
    # app.logger.info(f"Beta: {beta:.4f}")

    # 누적 수익률
    cumulative_return = (1 + portfolio_returns).prod() - 1

    # 연수 계산
    years = len(portfolio_returns) / trading_days

    # 연평균 수익률 (CAGR)
    if years > 0:
        cagr = (1 + cumulative_return) ** (1 / years) - 1
    else:
        cagr = 0

    # 벤치마크 CAGR 계산
    benchmark_cumulative_return = (1 + benchmark_returns).prod() - 1
    if years > 0:
        benchmark_cagr = (1 + benchmark_cumulative_return) ** (1 / years) - 1
    else:
        benchmark_cagr = 0

    # 알파 계산: CAGR 기반으로 수정
    # 알파 = 포트폴리오 CAGR - (베타 × 벤치마크 CAGR)
    # 이는 CAPM 모델: E(R) = Rf + β(Rm - Rf)에서 Rf=0 가정시
    # 알파 = 실제수익률 - 예상수익률 = CAGR - β × 벤치마크CAGR
    alpha = cagr - (beta * benchmark_cagr)

    # 벤치마크 샤프/소티노 계산
    benchmark_std = benchmark_returns.std() * np.sqrt(trading_days)
    benchmark_avg_return = (
        benchmark_returns.mean() * trading_days
    )  # 연간화된 평균 수익률
    benchmark_sharpe = benchmark_avg_return / benchmark_std if benchmark_std != 0 else 0

    benchmark_downside_returns = benchmark_returns[benchmark_returns < 0]
    benchmark_downside_std = benchmark_downside_returns.std() * np.sqrt(trading_days)
    benchmark_sortino = (
        benchmark_avg_return / benchmark_downside_std
        if benchmark_downside_std != 0
        else 0
    )

    # print(f"\n  📊 Benchmark metrics:")
    # print(f"    Sharpe: {benchmark_sharpe:.4f}")
    # print(f"    Sortino: {benchmark_sortino:.4f}")
    # print(f"    CAGR: {benchmark_cagr * 100:.2f}%")

    # 연 평균 수익률 (영업일 가중평균) 계산
    weighted_annual_return = calculate_weighted_annual_return(portfolio_returns)

    metrics = {
        "sharpe_ratio": round(sharpe_ratio, 4),
        "sortino_ratio": round(sortino_ratio, 4),
        "benchmark_sharpe_ratio": round(benchmark_sharpe, 4),
        "benchmark_sortino_ratio": round(benchmark_sortino, 4),
        "alpha": round(alpha * 100, 2),  # 퍼센트로 변환
        "beta": round(beta, 4),
        "annual_return": round(avg_return * 100, 2),  # 퍼센트로 변환
        "weighted_annual_return": round(
            weighted_annual_return * 100, 2
        ),  # 연 평균 수익률
        "benchmark_annual_return": round(benchmark_cagr * 100, 2),  # 벤치마크 CAGR
        "cagr": round(cagr * 100, 2),  # 퍼센트로 변환
        "cumulative_return": round(cumulative_return * 100, 2),
        "volatility": round(std_dev * 100, 2),
        "benchmark_volatility": round(benchmark_std * 100, 2),
    }

    return metrics


def prepare_chart_data(portfolio_returns, benchmark_returns, portfolio_series):
    """차트 데이터 준비"""
    # timezone 통일 (calculate_metrics와 동일)
    if (
        hasattr(portfolio_returns.index, "tz")
        and portfolio_returns.index.tz is not None
    ):
        portfolio_returns.index = portfolio_returns.index.tz_localize(None)

    if (
        hasattr(benchmark_returns.index, "tz")
        and benchmark_returns.index.tz is not None
    ):
        benchmark_returns.index = benchmark_returns.index.tz_localize(None)

    if hasattr(portfolio_series.index, "tz") and portfolio_series.index.tz is not None:
        portfolio_series.index = portfolio_series.index.tz_localize(None)

    common_dates = portfolio_returns.index.intersection(benchmark_returns.index)

    # 누적 수익률 계산
    portfolio_cumulative = (1 + portfolio_returns[common_dates]).cumprod()
    benchmark_cumulative = (1 + benchmark_returns[common_dates]).cumprod()

    # 날짜를 문자열로 변환
    dates = [date.strftime("%Y-%m-%d") for date in common_dates]

    chart_data = {
        "dates": dates,
        "portfolio_cumulative": [
            round(val, 4) for val in portfolio_cumulative.tolist()
        ],
        "benchmark_cumulative": [
            round(val, 4) for val in benchmark_cumulative.tolist()
        ],
        "portfolio_values": [
            round(val, 2) for val in portfolio_series[common_dates].tolist()
        ],
    }

    return chart_data


def prepare_allocation_data(
    portfolio_data, cash_holdings, total_initial_value_with_cash
):
    """도넛 차트용 자산 배분 데이터 준비"""

    # 시작 시점 배분
    initial_allocation = {}
    for ticker, data in portfolio_data.items():
        name = data.get("name", ticker)
        initial_allocation[name] = data["initial_value"]

    # 현금 추가
    for ticker, cash_data in cash_holdings.items():
        name = f"현금 ({cash_data['country']})"
        if name in initial_allocation:
            initial_allocation[name] += cash_data["value"]
        else:
            initial_allocation[name] = cash_data["value"]

    # 현재 시점 배분
    current_allocation = {}
    for ticker, data in portfolio_data.items():
        name = data.get("name", ticker)
        current_price = data["prices"].iloc[-1]
        current_value = current_price * data["quantity"]
        current_allocation[name] = current_value

    # 현금 추가 (현금은 가치 변동 없음)
    for ticker, cash_data in cash_holdings.items():
        name = f"현금 ({cash_data['country']})"
        if name in current_allocation:
            current_allocation[name] += cash_data["value"]
        else:
            current_allocation[name] = cash_data["value"]

    # 상위 10개 종목만 표시, 나머지는 "기타"로 묶기
    def get_top_allocations(allocation_dict, top_n=10):
        sorted_items = sorted(allocation_dict.items(), key=lambda x: x[1], reverse=True)

        if len(sorted_items) <= top_n:
            return dict(sorted_items)

        top_items = dict(sorted_items[:top_n])
        others_sum = sum(value for _, value in sorted_items[top_n:])
        if others_sum > 0:
            top_items["기타"] = others_sum

        return top_items

    initial_top = get_top_allocations(initial_allocation)
    current_top = get_top_allocations(current_allocation)

    return {
        "initial": {
            "labels": list(initial_top.keys()),
            "values": [round(v, 2) for v in initial_top.values()],
        },
        "current": {
            "labels": list(current_top.keys()),
            "values": [round(v, 2) for v in current_top.values()],
        },
    }


def prepare_holdings_table(
    portfolio_data: dict, cash_holdings: dict, base_currency: str, exchange_rate: float
):
    """보유 종목 테이블 데이터 준비 (현재 시점 기준)"""
    holdings = []

    # 투자 자산
    for ticker, data in portfolio_data.items():
        data: dict
        current_price = data["prices"].iloc[-1]
        quantity = data["quantity"]
        current_value = current_price * quantity
        name = data.get("name", ticker)

        holdings.append(
            {
                "ticker": ticker,
                "name": name,
                "quantity": quantity,
                "current_value": round(current_value, 2),
                "asset_class": data.get("asset_class", ""),
            }
        )

    # 현금
    for ticker, cash_data in cash_holdings.items():
        holdings.append(
            {
                "ticker": ticker,
                "name": f"현금 ({cash_data['country']})",
                "quantity": cash_data["value"],
                "current_value": round(cash_data["value"], 2),
                "asset_class": "현금",
            }
        )

    # 총 가치 계산
    total_value = sum(h["current_value"] for h in holdings)

    # 비중 계산
    for holding in holdings:
        holding["weight"] = (
            round((holding["current_value"] / total_value * 100), 2)
            if total_value > 0
            else 0
        )

    # 현재 가치 기준 정렬
    holdings.sort(key=lambda x: x["current_value"], reverse=True)

    return holdings


@app.route("/")
def index():
    """메인 페이지"""
    return render_template("index.html", active_page="analyze")


@app.route("/api/cache-stats", methods=["GET"])
def get_cache_stats():
    """캐시 통계 조회"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # 캐시된 티커 수와 레코드 수 조회
        cursor.execute(
            """
            SELECT COUNT(DISTINCT ticker) as ticker_count,
                   COUNT(*) as record_count
            FROM stock_price_cache
        """
        )

        result = cursor.fetchone()
        ticker_count = result[0] if result else 0
        record_count = result[1] if result else 0

        return jsonify({"ticker_count": ticker_count, "record_count": record_count})
    except Exception as e:
        print(f"Error getting cache stats: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/save-portfolio", methods=["POST"])
def save_portfolio():
    """포트폴리오 분석 결과 저장"""
    try:
        # 로그인 체크 - 필수
        if "user_id" not in session:
            return jsonify({"error": "로그인이 필요한 기능입니다."}), 401

        user_id = session["user_id"]

        data = request.json

        # 필수 데이터 확인
        required_fields = [
            "name",
            "csv_content",
            "start_date",
            "benchmark_ticker",
            "base_currency",
            "metrics",
            "summary",
            "holdings_table",
            "allocation_data",
            "chart_data",
        ]

        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return (
                jsonify({"error": f"필수 데이터 누락: {', '.join(missing_fields)}"}),
                400,
            )

        # JSON으로 변환하여 저장
        import json

        portfolio = SavedPortfolio(
            user_id=user_id,
            name=data["name"],
            csv_content=data["csv_content"],
            start_date=data["start_date"],
            benchmark_ticker=data["benchmark_ticker"],
            base_currency=data["base_currency"],
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )

        # 분석 결과를 csv_content에 JSON으로 추가 저장
        full_data = {
            "csv_content": data["csv_content"],
            "metrics": data["metrics"],
            "summary": data["summary"],
            "holdings_table": data["holdings_table"],
            "allocation_data": data["allocation_data"],
            "chart_data": data["chart_data"],
        }
        portfolio.csv_content = json.dumps(full_data, ensure_ascii=False)

        db.session.add(portfolio)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "portfolio_id": portfolio.id,
                "message": f"포트폴리오 '{data['name']}'가 저장되었습니다.",
            }
        )

    except Exception as e:
        db.session.rollback()
        error_trace = traceback.format_exc()
        print("=" * 80)
        print("❌ ERROR in /api/save-portfolio endpoint:")
        print(error_trace)
        print("=" * 80)
        return jsonify({"error": f"저장 중 오류가 발생했습니다: {str(e)}"}), 500


@app.route("/api/exchange-rate", methods=["GET"])
def get_exchange_rate():
    """환율 데이터 조회 (USD/KRW)"""
    try:
        start_date = request.args.get("start_date", "2000-01-01")
        end_date = request.args.get("end_date", datetime.now().strftime("%Y-%m-%d"))

        # 날짜 파싱
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # DB에서 기존 데이터 조회
        existing_data = ExchangeRateCache.query.filter(
            ExchangeRateCache.date >= start_date, ExchangeRateCache.date <= end_date
        ).all()

        # 날짜별 데이터를 딕셔너리로 변환
        existing_dict = {data.date: data for data in existing_data}

        # DB에 데이터가 없거나 최근 데이터가 없는 경우만 다운로드
        need_download = False
        if not existing_data:
            print("📥 DB에 환율 데이터가 없습니다. 전체 다운로드를 시작합니다...")
            need_download = True
        else:
            # 가장 최근 날짜 확인
            latest_date = max(data.date for data in existing_data)
            latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
            today = datetime.now().date()

            # 오늘 날짜보다 이전이면 업데이트 (주말 제외 자동 처리)
            if latest_dt.date() < today:
                print(
                    f"📥 최근 환율 데이터 업데이트 중... (마지막 날짜: {latest_date})"
                )
                need_download = True
                start_date = latest_date  # 마지막 날짜부터만 다운로드

        # 필요한 경우만 Yahoo Finance에서 가져오기
        if need_download:
            # Yahoo Finance에서 USD/KRW 데이터 가져오기
            ticker = yf.Ticker("KRW=X")

            hist = ticker.history(start=start_date, end=end_date, interval="1d")

            if not hist.empty:
                new_count = 0
                # 데이터를 DB에 저장
                for date_idx, row in hist.iterrows():
                    date_str = date_idx.strftime("%Y-%m-%d")

                    # 이미 존재하는지 확인
                    if date_str not in existing_dict:
                        exchange_rate = ExchangeRateCache(
                            date=date_str,
                            open=(
                                float(row["Open"])
                                if not pd.isna(row["Open"])
                                else float(row["Close"])
                            ),
                            high=(
                                float(row["High"])
                                if not pd.isna(row["High"])
                                else float(row["Close"])
                            ),
                            low=(
                                float(row["Low"])
                                if not pd.isna(row["Low"])
                                else float(row["Close"])
                            ),
                            close=float(row["Close"]),
                            volume=(
                                float(row["Volume"])
                                if not pd.isna(row["Volume"])
                                else 0
                            ),
                        )
                        db.session.add(exchange_rate)
                        existing_dict[date_str] = exchange_rate
                        new_count += 1

                db.session.commit()
                print(
                    f"✅ 환율 데이터 {new_count}일 분량 저장 완료 (전체: {len(existing_dict)}일)"
                )
            else:
                print("⚠️ Yahoo Finance에서 데이터를 가져올 수 없습니다.")

        # 요청된 날짜 범위의 데이터 반환
        result = []
        for date_str, data in existing_dict.items():
            result.append(
                {
                    "date": data.date,
                    "open": data.open,
                    "high": data.high,
                    "low": data.low,
                    "close": data.close,
                    "volume": data.volume,
                }
            )

        # 날짜순 정렬
        result.sort(key=lambda x: x["date"])

        return jsonify({"success": True, "data": result, "count": len(result)})

    except Exception as e:
        error_trace = traceback.format_exc()
        print("=" * 80)
        print("❌ ERROR in /api/exchange-rate endpoint:")
        print(error_trace)
        print("=" * 80)
        return jsonify({"error": f"환율 데이터 조회 중 오류: {str(e)}"}), 500


@app.route("/api/exchange-rate/indicators", methods=["GET"])
def get_exchange_rate_indicators():
    """환율 기술적 지표 계산"""
    try:
        from ta.trend import SMAIndicator, IchimokuIndicator, MACD
        from ta.volatility import BollingerBands
        from ta.momentum import ROCIndicator

        start_date = request.args.get("start_date", "2000-01-01")
        end_date = request.args.get("end_date", datetime.now().strftime("%Y-%m-%d"))

        # 전체 데이터 조회 (지표 계산을 위해)
        all_data = (
            ExchangeRateCache.query.filter(
                ExchangeRateCache.date >= start_date, ExchangeRateCache.date <= end_date
            )
            .order_by(ExchangeRateCache.date)
            .all()
        )

        if not all_data:
            return jsonify({"success": False, "error": "데이터가 없습니다"}), 404

        # DataFrame 생성
        df = pd.DataFrame(
            [
                {
                    "date": d.date,
                    "open": d.open,
                    "high": d.high,
                    "low": d.low,
                    "close": d.close,
                    "volume": d.volume,
                }
                for d in all_data
            ]
        )

        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

        # 기술적 지표 계산
        indicators = {}

        # 이동평균선
        indicators["ma5"] = (
            SMAIndicator(close=df["close"], window=5).sma_indicator().bfill().tolist()
        )
        indicators["ma10"] = (
            SMAIndicator(close=df["close"], window=10).sma_indicator().bfill().tolist()
        )
        indicators["ma20"] = (
            SMAIndicator(close=df["close"], window=20).sma_indicator().bfill().tolist()
        )
        indicators["ma50"] = (
            SMAIndicator(close=df["close"], window=50).sma_indicator().bfill().tolist()
        )
        indicators["ma120"] = (
            SMAIndicator(close=df["close"], window=120).sma_indicator().bfill().tolist()
        )
        indicators["ma200"] = (
            SMAIndicator(close=df["close"], window=200).sma_indicator().bfill().tolist()
        )

        # 볼린저 밴드
        bb = BollingerBands(close=df["close"], window=20, window_dev=2)
        indicators["bollinger"] = {
            "upper": bb.bollinger_hband().bfill().tolist(),
            "middle": bb.bollinger_mavg().bfill().tolist(),
            "lower": bb.bollinger_lband().bfill().tolist(),
        }

        # 일목균형표 - 수동 계산 (선행/후행 스팬 처리)
        def calculate_ichimoku_manual(high, low, close):
            # 전환선 (9일)
            tenkan_period = 9
            tenkan = []
            for i in range(len(high)):
                if i < tenkan_period - 1:
                    tenkan.append(None)
                else:
                    period_high = high[i - tenkan_period + 1 : i + 1].max()
                    period_low = low[i - tenkan_period + 1 : i + 1].min()
                    tenkan.append((period_high + period_low) / 2)

            # 기준선 (26일)
            kijun_period = 26
            kijun = []
            for i in range(len(high)):
                if i < kijun_period - 1:
                    kijun.append(None)
                else:
                    period_high = high[i - kijun_period + 1 : i + 1].max()
                    period_low = low[i - kijun_period + 1 : i + 1].min()
                    kijun.append((period_high + period_low) / 2)

            # 선행스팬A: (전환선 + 기준선) / 2, 26일 선행
            senkou_a = []
            for i in range(len(high)):
                if tenkan[i] is not None and kijun[i] is not None:
                    senkou_a.append((tenkan[i] + kijun[i]) / 2)
                else:
                    senkou_a.append(None)
            # 26일 선행 (미래로 이동)
            senkou_a = [None] * 26 + senkou_a

            # 선행스팬B: (52일 최고가 + 최저가) / 2, 26일 선행
            senkou_b_period = 52
            senkou_b = []
            for i in range(len(high)):
                if i < senkou_b_period - 1:
                    senkou_b.append(None)
                else:
                    period_high = high[i - senkou_b_period + 1 : i + 1].max()
                    period_low = low[i - senkou_b_period + 1 : i + 1].min()
                    senkou_b.append((period_high + period_low) / 2)
            # 26일 선행 (미래로 이동)
            senkou_b = [None] * 26 + senkou_b

            # 후행스팬: 현재 종가, 26일 후행 (과거로 이동)
            chikou = close.tolist()[26:] + [None] * 26

            return {
                "tenkan": tenkan,
                "kijun": kijun,
                "senkou_a": senkou_a[: len(high) + 26],  # 미래 26일 포함
                "senkou_b": senkou_b[: len(high) + 26],  # 미래 26일 포함
                "chikou": chikou,
                "future_dates": 26,  # 미래 날짜 개수
            }

        ichimoku_data = calculate_ichimoku_manual(df["high"], df["low"], df["close"])

        # 미래 날짜 생성 (26일)
        last_date = df.index[-1]
        future_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1), periods=26, freq="D"
        )
        all_dates = df.index.tolist() + future_dates.tolist()

        indicators["ichimoku"] = {
            "tenkan": ichimoku_data["tenkan"],
            "kijun": ichimoku_data["kijun"],
            "senkou_a": ichimoku_data["senkou_a"],
            "senkou_b": ichimoku_data["senkou_b"],
            "chikou": ichimoku_data["chikou"],
        }

        # MACD
        macd = MACD(close=df["close"], window_slow=26, window_fast=12, window_sign=9)
        indicators["macd"] = {
            "macd": macd.macd().fillna(0).tolist(),
            "signal": macd.macd_signal().fillna(0).tolist(),
            "histogram": macd.macd_diff().fillna(0).tolist(),
        }

        # 모멘텀 (ROC - Rate of Change)
        roc = ROCIndicator(close=df["close"], window=10)
        indicators["momentum"] = roc.roc().fillna(0).tolist()

        # 날짜 리스트 (미래 26일 포함 - 일목균형표용)
        dates = [d.strftime("%Y-%m-%d") for d in all_dates]

        return jsonify({"success": True, "dates": dates, "indicators": indicators})

    except Exception as e:
        error_trace = traceback.format_exc()
        print("=" * 80)
        print("❌ ERROR in /api/exchange-rate/indicators endpoint:")
        print(error_trace)
        print("=" * 80)
        return jsonify({"error": f"지표 계산 중 오류: {str(e)}"}), 500


@app.route("/ranking")
def ranking():
    """랭킹 페이지"""
    return render_template("ranking.html", active_page="ranking")


# @app.route("/exchange-rate")
# def exchange_rate():
#     """환율 페이지"""
#     return render_template("exchange_rate.html", active_page="exchange-rate")


@app.route("/login")
def login():
    """로그인 페이지"""
    # 이미 로그인된 경우 메인 페이지로 리다이렉트
    if "user_id" in session:
        return redirect("/")
    return render_template("login.html", active_page="login")


@app.route("/signup")
def signup():
    """회원가입 페이지"""
    return render_template("signup.html", active_page="signup")


@app.route("/mypage")
def mypage():
    """마이페이지"""
    # 로그인 확인
    if "user_id" not in session:
        return redirect("/login")

    # 사용자 정보 조회
    user = User.query.filter_by(id=session["user_id"]).first()
    is_admin = user.is_admin if user else False

    return render_template("mypage.html", active_page="mypage", is_admin=is_admin)


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    """관리자 로그인 페이지"""
    if request.method == "POST":
        password = request.form.get("password")
        admin_password = os.getenv("ADMIN_PW")

        if not admin_password:
            return render_template(
                "admin_login.html", error="관리자 비밀번호가 설정되지 않았습니다."
            )

        if password == admin_password:
            session["admin_authenticated"] = True
            session.permanent = True  # 세션 유지
            next_url = request.args.get("next", "/admin")
            return redirect(next_url)
        else:
            return render_template(
                "admin_login.html", error="비밀번호가 올바르지 않습니다."
            )

    return render_template("admin_login.html")


@app.route("/admin-logout")
def admin_logout():
    """관리자 로그아웃"""
    session.pop("admin_authenticated", None)
    return redirect("/")


@app.route("/api/update-nickname", methods=["POST"])
def update_nickname():
    """닉네임 변경"""
    try:
        # 로그인 확인
        if "user_id" not in session:
            return jsonify({"error": "로그인이 필요합니다."}), 401

        data = request.json
        new_nickname = data.get("nickname")

        if not new_nickname:
            return jsonify({"error": "닉네임을 입력해주세요."}), 400

        # 닉네임 길이 체크
        if len(new_nickname) < 2 or len(new_nickname) > 20:
            return jsonify({"error": "닉네임은 2~20자 사이여야 합니다."}), 400

        # 현재 사용자
        user = User.query.get(session["user_id"])
        if not user:
            return jsonify({"error": "사용자를 찾을 수 없습니다."}), 404

        # 현재 닉네임과 같은지 확인
        if user.nickname == new_nickname:
            return jsonify({"error": "현재 닉네임과 동일합니다."}), 400

        # 닉네임 중복 체크
        existing_user = User.query.filter_by(nickname=new_nickname).first()
        if existing_user:
            return jsonify({"error": "이미 사용 중인 닉네임입니다."}), 400

        # 닉네임 변경
        old_nickname = user.nickname
        user.nickname = new_nickname
        db.session.commit()

        # 세션 업데이트
        session["nickname"] = new_nickname

        app.logger.info(f"✅ 닉네임 변경: {old_nickname} -> {new_nickname}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "닉네임이 변경되었습니다.",
                    "nickname": new_nickname,
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"닉네임 변경 오류: {e}")
        traceback.print_exc()
        return jsonify({"error": "닉네임 변경 중 오류가 발생했습니다."}), 500


@app.route("/api/my-portfolios", methods=["GET"])
def get_my_portfolios():
    """내 포트폴리오 목록 조회"""
    try:
        # 로그인 확인
        if "user_id" not in session:
            return jsonify({"error": "로그인이 필요합니다."}), 401

        import json

        # 사용자의 포트폴리오 조회
        portfolios = (
            SavedPortfolio.query.filter_by(user_id=session["user_id"])
            .order_by(SavedPortfolio.last_accessed.desc())
            .all()
        )

        result = []
        for p in portfolios:
            try:
                data = json.loads(p.csv_content)
                metrics = data.get("metrics", {})
                summary = data.get("summary", {})

                result.append(
                    {
                        "id": p.id,
                        "name": p.name,
                        "benchmark": p.benchmark_ticker,
                        "base_currency": p.base_currency,
                        "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
                        "last_accessed": p.last_accessed.strftime("%Y-%m-%d %H:%M"),
                        "metrics": metrics,
                        "summary": summary,
                    }
                )
            except Exception as e:
                app.logger.error(f"포트폴리오 {p.id} 파싱 오류: {e}")
                continue

        return (
            jsonify({"success": True, "portfolios": result, "count": len(result)}),
            200,
        )

    except Exception as e:
        app.logger.error(f"포트폴리오 조회 오류: {e}")
        traceback.print_exc()
        return jsonify({"error": "포트폴리오 조회 중 오류가 발생했습니다."}), 500


@app.route("/api/delete-portfolio/<int:portfolio_id>", methods=["DELETE"])
def delete_portfolio(portfolio_id):
    """포트폴리오 삭제"""
    try:
        # 로그인 확인
        if "user_id" not in session:
            return jsonify({"error": "로그인이 필요합니다."}), 401

        user_id = session["user_id"]

        # 포트폴리오 조회
        portfolio = SavedPortfolio.query.get(portfolio_id)

        if not portfolio:
            return jsonify({"error": "포트폴리오를 찾을 수 없습니다."}), 404

        # 소유권 확인 - 필수!
        if portfolio.user_id != user_id:
            app.logger.warning(
                f"⚠️ 권한 없는 삭제 시도: User {user_id} -> Portfolio {portfolio_id} (Owner: {portfolio.user_id})"
            )
            return jsonify({"error": "본인의 포트폴리오만 삭제할 수 있습니다."}), 403

        # 포트폴리오 삭제
        portfolio_name = portfolio.name
        db.session.delete(portfolio)
        db.session.commit()

        app.logger.info(
            f"✅ 포트폴리오 삭제 완료: {portfolio_name} (ID: {portfolio_id}) by User {user_id}"
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"'{portfolio_name}' 포트폴리오가 삭제되었습니다.",
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"포트폴리오 삭제 오류: {e}")
        traceback.print_exc()
        return jsonify({"error": "포트폴리오 삭제 중 오류가 발생했습니다."}), 500


@app.route("/api/login", methods=["POST"])
def api_login():
    """로그인 처리"""
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")

        # 필수 필드 검증
        if not email or not password:
            return jsonify({"error": "이메일과 비밀번호를 입력해주세요."}), 400

        # 사용자 조회
        user = User.query.filter_by(email=email).first()

        if not user:
            return jsonify({"error": "이메일 또는 비밀번호가 일치하지 않습니다."}), 401

        # 소셜 로그인 계정 체크
        if user.account_type != "local":
            return (
                jsonify(
                    {
                        "error": f"{user.account_type.upper()} 계정입니다. 해당 소셜 로그인을 이용해주세요."
                    }
                ),
                400,
            )

        # 비밀번호 검증
        if not verify_password(password, user.password_hash):
            return jsonify({"error": "이메일 또는 비밀번호가 일치하지 않습니다."}), 401

        # 활성화 상태 확인
        if not user.is_active:
            return (
                jsonify({"error": "비활성화된 계정입니다. 관리자에게 문의하세요."}),
                403,
            )

        # 세션에 사용자 정보 저장
        session.clear()  # 기존 세션 클리어
        session["user_id"] = user.id
        session["email"] = user.email
        session["nickname"] = user.nickname
        session["account_type"] = user.account_type
        session.permanent = True  # 세션 유지 (7일)

        # 마지막 로그인 시간 업데이트
        user.last_login = datetime.now()
        db.session.commit()

        app.logger.info(f"✅ 로그인 성공: {email} ({user.nickname})")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "로그인되었습니다.",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "nickname": user.nickname,
                        "account_type": user.account_type,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        app.logger.error(f"로그인 오류: {e}")
        traceback.print_exc()
        return jsonify({"error": "로그인 중 오류가 발생했습니다."}), 500


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """로그아웃 처리"""
    try:
        email = session.get("email", "Unknown")
        session.clear()
        app.logger.info(f"✅ 로그아웃: {email}")

        return jsonify({"success": True, "message": "로그아웃되었습니다."}), 200

    except Exception as e:
        app.logger.error(f"로그아웃 오류: {e}")
        return jsonify({"error": "로그아웃 중 오류가 발생했습니다."}), 500


@app.route("/api/me", methods=["GET"])
def get_current_user():
    """현재 로그인한 사용자 정보 조회"""
    try:
        if "user_id" not in session:
            return jsonify({"logged_in": False}), 200

        user = User.query.get(session["user_id"])

        if not user:
            session.clear()
            return jsonify({"logged_in": False}), 200

        return (
            jsonify(
                {
                    "logged_in": True,
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "nickname": user.nickname,
                        "account_type": user.account_type,
                        "is_admin": user.is_admin,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        app.logger.error(f"사용자 정보 조회 오류: {e}")
        return jsonify({"error": "사용자 정보 조회 중 오류가 발생했습니다."}), 500


@app.route("/api/check-email", methods=["POST"])
def check_email():
    """이메일 중복 체크"""
    try:
        data = request.json
        email = data.get("email")

        if not email:
            return jsonify({"error": "이메일을 입력해주세요."}), 400

        # 이메일 형식 검증
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return jsonify({"error": "올바른 이메일 형식이 아닙니다."}), 400

        # 중복 체크
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return (
                jsonify({"exists": True, "message": "이미 가입된 이메일입니다."}),
                200,
            )

        return jsonify({"exists": False, "message": "사용 가능한 이메일입니다."}), 200

    except Exception as e:
        app.logger.error(f"이메일 체크 오류: {e}")
        return jsonify({"error": "이메일 확인 중 오류가 발생했습니다."}), 500


@app.route("/api/send-verification", methods=["POST"])
def send_verification():
    """이메일 인증번호 전송"""
    try:
        data = request.json
        email = data.get("email")

        if not email:
            return jsonify({"error": "이메일을 입력해주세요."}), 400

        # 이미 가입된 이메일인지 체크
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"error": "이미 가입된 이메일입니다."}), 400

        # DEBUG 모드인 경우 자동 인증 처리
        if DEBUG:
            # 기존 인증번호 삭제
            EmailVerification.query.filter_by(email=email).delete()

            # 자동 인증 완료된 레코드 생성
            code = "000000"
            expires_at = datetime.now() + timedelta(minutes=5)
            verification = EmailVerification(
                email=email,
                code=code,
                expires_at=expires_at,
                is_verified=True,  # DEBUG 모드에서는 바로 인증 완료
            )
            db.session.add(verification)
            db.session.commit()

            app.logger.info(f"🔧 [DEBUG 모드] 이메일 자동 인증: {email}")
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "[DEBUG 모드] 이메일 인증이 자동으로 완료되었습니다.",
                        "expires_in": 300,
                        "debug_mode": True,
                    }
                ),
                200,
            )

        # 기존 인증번호 삭제 (같은 이메일)
        EmailVerification.query.filter_by(email=email, is_verified=False).delete()

        # 인증번호 생성
        code = generate_verification_code()
        expires_at = datetime.now() + timedelta(minutes=5)

        # DB에 저장
        verification = EmailVerification(email=email, code=code, expires_at=expires_at)
        db.session.add(verification)
        db.session.commit()

        # 이메일 전송
        if send_verification_email(email, code):
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "인증번호가 이메일로 전송되었습니다.",
                        "expires_in": 300,  # 5분
                    }
                ),
                200,
            )
        else:
            return jsonify({"error": "이메일 전송에 실패했습니다."}), 500

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"인증번호 전송 오류: {e}")
        return jsonify({"error": "인증번호 전송 중 오류가 발생했습니다."}), 500


@app.route("/api/verify-code", methods=["POST"])
def verify_code():
    """인증번호 확인"""
    try:
        data = request.json
        email = data.get("email")
        code = data.get("code")

        if not email or not code:
            return jsonify({"error": "이메일과 인증번호를 입력해주세요."}), 400

        # DEBUG 모드인 경우 모든 인증번호 통과
        if DEBUG:
            # 이미 인증된 레코드가 있는지 확인
            verification = (
                EmailVerification.query.filter_by(email=email, is_verified=True)
                .order_by(EmailVerification.created_at.desc())
                .first()
            )

            # 없으면 새로 생성
            if not verification:
                verification = EmailVerification(
                    email=email,
                    code="000000",
                    expires_at=datetime.now() + timedelta(minutes=5),
                    is_verified=True,
                )
                db.session.add(verification)
                db.session.commit()

            app.logger.info(f"🔧 [DEBUG 모드] 인증번호 자동 통과: {email}")
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "[DEBUG 모드] 이메일 인증이 자동으로 완료되었습니다.",
                    }
                ),
                200,
            )

        # 인증번호 조회
        verification = (
            EmailVerification.query.filter_by(email=email, code=code, is_verified=False)
            .order_by(EmailVerification.created_at.desc())
            .first()
        )

        if not verification:
            return jsonify({"error": "잘못된 인증번호입니다."}), 400

        # 만료 시간 체크
        if datetime.now() > verification.expires_at:
            return (
                jsonify({"error": "인증번호가 만료되었습니다. 다시 요청해주세요."}),
                400,
            )

        # 인증 완료 처리
        verification.is_verified = True
        db.session.commit()

        return (
            jsonify({"success": True, "message": "이메일 인증이 완료되었습니다."}),
            200,
        )

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"인증번호 확인 오류: {e}")
        return jsonify({"error": "인증번호 확인 중 오류가 발생했습니다."}), 500


@app.route("/api/check-nickname", methods=["POST"])
def check_nickname():
    """닉네임 중복 체크"""
    try:
        data = request.json
        nickname = data.get("nickname")

        if not nickname:
            return jsonify({"error": "닉네임을 입력해주세요."}), 400

        # 닉네임 길이 체크
        if len(nickname) < 2 or len(nickname) > 20:
            return jsonify({"error": "닉네임은 2~20자 사이여야 합니다."}), 400

        # 중복 체크
        existing_user = User.query.filter_by(nickname=nickname).first()

        if existing_user:
            return (
                jsonify({"exists": True, "message": "이미 사용 중인 닉네임입니다."}),
                200,
            )

        return jsonify({"exists": False, "message": "사용 가능한 닉네임입니다."}), 200

    except Exception as e:
        app.logger.error(f"닉네임 체크 오류: {e}")
        return jsonify({"error": "닉네임 확인 중 오류가 발생했습니다."}), 500


@app.route("/api/signup", methods=["POST"])
def api_signup():
    """회원가입 처리"""
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")
        nickname = data.get("nickname")
        account_type = data.get("account_type", "local")  # 기본값: local

        # 필수 필드 검증
        if not email or not nickname:
            return jsonify({"error": "이메일과 닉네임을 입력해주세요."}), 400

        # 로컬 가입인 경우 비밀번호 필수
        if account_type == "local" and not password:
            return jsonify({"error": "비밀번호를 입력해주세요."}), 400

        # account_type 검증
        if account_type not in ["local", "google", "kakao"]:
            return jsonify({"error": "올바른 회원 유형이 아닙니다."}), 400

        # 이메일 인증 확인 (로컬 가입만)
        if account_type == "local":
            verification = (
                EmailVerification.query.filter_by(email=email, is_verified=True)
                .order_by(EmailVerification.created_at.desc())
                .first()
            )

            if not verification:
                return jsonify({"error": "이메일 인증이 완료되지 않았습니다."}), 400

        # 이메일 중복 체크 (재확인)
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "이미 가입된 이메일입니다."}), 400

        # 닉네임 중복 체크 (재확인)
        if User.query.filter_by(nickname=nickname).first():
            return jsonify({"error": "이미 사용 중인 닉네임입니다."}), 400

        # 비밀번호 해싱 (로컬 가입만)
        password_hash = None
        if account_type == "local":
            password_hash = hash_password(password)

        # 사용자 생성
        new_user = User(
            email=email,
            password_hash=password_hash,
            nickname=nickname,
            account_type=account_type,
        )

        db.session.add(new_user)
        db.session.commit()

        app.logger.info(f"✅ 회원가입 성공: {email} ({nickname}) - {account_type}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "회원가입이 완료되었습니다.",
                    "user_id": new_user.id,
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"회원가입 오류: {e}")
        traceback.print_exc()
        return jsonify({"error": "회원가입 중 오류가 발생했습니다."}), 500


@app.route("/api/rankings", methods=["GET"])
def get_rankings():
    """포트폴리오 랭킹 데이터 조회"""
    try:
        import json

        # 벤치마크 필터 파라미터 받기
        benchmark_filter = request.args.get("benchmark", None)

        # 벤치마크 매핑 (프론트엔드 표시명 -> 실제 티커들)
        # 여러 가능한 티커를 리스트로 관리
        benchmark_mapping = {
            "S&P500": ["SPY", "^GSPC"],
            "NASDAQ100": ["QQQ", "^NDX"],
            "KODEX200": ["069500.KS"],
        }

        portfolios = SavedPortfolio.query.all()

        if not portfolios:
            return jsonify(
                {"cagr": [], "sortino": [], "sharpe": [], "alpha": [], "beta": []}
            )

        # 포트폴리오 데이터 파싱
        portfolio_list = []
        for p in portfolios:
            p: SavedPortfolio
            try:
                data = json.loads(p.csv_content)

                # 벤치마크 필터링
                if benchmark_filter and benchmark_filter != "전체":
                    expected_tickers = benchmark_mapping.get(benchmark_filter, [])
                    # benchmark_ticker가 없거나 일치하지 않으면 스킵
                    if (
                        not p.benchmark_ticker
                        or p.benchmark_ticker not in expected_tickers
                    ):
                        continue

                # 사용자 닉네임 가져오기
                owner_nickname = "익명"
                if p.user_id:
                    owner = User.query.get(p.user_id)
                    if owner:
                        owner_nickname = owner.nickname

                # 벤치마크 이름 가져오기
                summary = data.get("summary", {})
                benchmark_name = summary.get("benchmark_name", p.benchmark_ticker)

                portfolio_list.append(
                    {
                        "id": p.id,
                        "name": p.name,
                        "created_at": p.created_at.isoformat(),
                        "benchmark": p.benchmark_ticker,
                        "benchmark_name": benchmark_name,
                        "owner_nickname": owner_nickname,
                        "metrics": data.get("metrics", {}),
                    }
                )
            except Exception as e:
                print(f"Error parsing portfolio {p.id}: {e}")
                continue

        # 각 지표별 Top 5
        cagr_top = sorted(
            portfolio_list,
            key=lambda x: x["metrics"].get("cagr", -999999),
            reverse=True,
        )[:5]
        sortino_top = sorted(
            portfolio_list,
            key=lambda x: x["metrics"].get("sortino_ratio", -999999),
            reverse=True,
        )[:5]
        sharpe_top = sorted(
            portfolio_list,
            key=lambda x: x["metrics"].get("sharpe_ratio", -999999),
            reverse=True,
        )[:5]
        alpha_top = sorted(
            portfolio_list,
            key=lambda x: x["metrics"].get("alpha", -999999),
            reverse=True,
        )[:5]

        # 베타는 1.0에 가까운 순
        beta_top = sorted(
            portfolio_list, key=lambda x: abs(x["metrics"].get("beta", 999999) - 1.0)
        )[:5]

        return jsonify(
            {
                "cagr": cagr_top,
                "sortino": sortino_top,
                "sharpe": sharpe_top,
                "alpha": alpha_top,
                "beta": beta_top,
            }
        )

    except Exception as e:
        error_trace = traceback.format_exc()
        print("=" * 80)
        print("❌ ERROR in /api/rankings endpoint:")
        print(error_trace)
        print("=" * 80)
        return jsonify({"error": str(e)}), 500


@app.route("/portfolio/<int:portfolio_id>")
def view_portfolio(portfolio_id):
    """저장된 포트폴리오 상세보기"""
    try:
        import json

        portfolio: SavedPortfolio = SavedPortfolio.query.get_or_404(portfolio_id)

        # 마지막 접근 시간 업데이트
        portfolio.last_accessed = datetime.now()
        db.session.commit()

        # 데이터 파싱
        data = json.loads(portfolio.csv_content)

        # 사용자 닉네임 가져오기
        owner_nickname = "익명"
        if portfolio.user_id:
            owner = User.query.get(portfolio.user_id)
            if owner:
                owner_nickname = owner.nickname

        # 소유자 여부 확인
        is_owner = False
        if "user_id" in session and portfolio.user_id == session["user_id"]:
            is_owner = True

        # 분석 결과 페이지에 전달
        return render_template(
            "portfolio_view.html",
            portfolio=portfolio,
            data=data,
            owner_nickname=owner_nickname,
            is_owner=is_owner,
        )

    except Exception as e:
        error_trace = traceback.format_exc()
        app.logger.warning("❌ ERROR in /portfolio/<id> endpoint:")
        app.logger.warning(error_trace)
        return f"포트폴리오를 불러올 수 없습니다: {str(e)}", 500


@app.route("/parse-csv", methods=["POST"])
def parse_csv():
    """CSV 파일을 파싱하여 포트폴리오 데이터 반환"""
    try:
        # CSV 파일 읽기
        if "csv_file" not in request.files:
            return jsonify({"error": "CSV 파일이 업로드되지 않았습니다."}), 400

        file = request.files["csv_file"]

        if file.filename == "":
            return jsonify({"error": "파일이 선택되지 않았습니다."}), 400

        app.logger.info(f"📁 Parsing CSV file: {file.filename}")

        # CSV 파일 파싱
        csv_content = file.read().decode("utf-8")
        portfolio_df = pd.read_csv(io.StringIO(csv_content))

        # 필수 컬럼 확인
        required_columns = ["티커", "보유량", "국가"]
        missing_columns = [
            col for col in required_columns if col not in portfolio_df.columns
        ]

        if missing_columns:
            return (
                jsonify(
                    {
                        "error": f'CSV 파일에 다음 컬럼이 필요합니다: {", ".join(missing_columns)}'
                    }
                ),
                400,
            )

        # 데이터 변환
        portfolio_data = []
        for _, row in portfolio_df.iterrows():
            ticker = row["티커"]
            quantity = row["보유량"]
            country = row["국가"]
            classification = row.get("분류", "")

            # 분류가 "현금"인 경우 별도 처리
            if classification == "현금":
                continue

            portfolio_data.append(
                {
                    "ticker": ticker,
                    "quantity": float(quantity),
                    "country": country,
                }
            )

        # 현금 데이터 추출
        cash_data = {"KRW": 0, "USD": 0}
        cash_rows = portfolio_df[portfolio_df.get("분류", "") == "현금"]
        for _, row in cash_rows.iterrows():
            country = row["국가"]
            amount = float(row["보유량"])
            if country == "한국":
                cash_data["KRW"] += amount
            elif country == "미국":
                cash_data["USD"] += amount

        app.logger.info(
            f"✅ CSV parsed: {len(portfolio_data)} stocks, KRW: {cash_data['KRW']}, USD: {cash_data['USD']}"
        )

        return jsonify(
            {
                "success": True,
                "portfolio": portfolio_data,
                "cash": cash_data,
            }
        )

    except Exception as e:
        app.logger.error(f"❌ Error parsing CSV: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"CSV 파일 파싱 오류: {str(e)}"}), 400


@app.route("/analyze", methods=["POST"])
def analyze():
    """포트폴리오 분석"""
    try:
        # CSV 파일 읽기
        if "csv_file" not in request.files:
            return jsonify({"error": "CSV 파일이 업로드되지 않았습니다."}), 400

        file = request.files["csv_file"]

        if file.filename == "":
            return jsonify({"error": "파일이 선택되지 않았습니다."}), 400

        app.logger.info(f"📁 Received file: {file.filename}")

        start_date = request.form.get("start_date")
        benchmark_ticker = request.form.get("benchmark_ticker")
        base_currency = request.form.get("base_currency", "USD")

        if not start_date or not benchmark_ticker:
            return jsonify({"error": "시작 일자와 벤치마크 티커를 입력해주세요."}), 400

        # CSV 파일 파싱
        csv_content = file.read().decode("utf-8")
        app.logger.info(f"📄 CSV content length: {len(csv_content)} bytes")

        portfolio_df = pd.read_csv(io.StringIO(csv_content))

        # 필수 컬럼 확인
        required_columns = ["티커", "보유량", "국가", "분류"]
        missing_columns = [
            col for col in required_columns if col not in portfolio_df.columns
        ]

        if missing_columns:
            return (
                jsonify(
                    {
                        "error": f'CSV 파일에 다음 컬럼이 필요합니다: {", ".join(missing_columns)}'
                    }
                ),
                400,
            )

        # 동일 티커 병합
        portfolio_df = merge_duplicate_tickers(portfolio_df)

        # 날짜 변환
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")

        # DCA 데이터 처리
        dca_data = None
        dca_data_json = request.form.get("dca_data")
        if dca_data_json:
            try:
                dca_data = json.loads(dca_data_json)
                app.logger.info(f"📈 Received DCA data: {dca_data}")
            except json.JSONDecodeError as e:
                app.logger.error(f"❌ Error parsing DCA data: {e}")
                dca_data = None

        # 포트폴리오 수익률 계산
        # DCA가 있으면 시뮬레이션 함수 사용, 없으면 일반 함수 사용
        if dca_data and len(dca_data) > 0:
            app.logger.info("📈 Using DCA simulation mode")
            result = calculate_portfolio_returns_with_dca(
                portfolio_df, dca_data, start_date_obj, base_currency
            )
        else:
            app.logger.info("📊 Using standard portfolio calculation")
            result = calculate_portfolio_returns(
                portfolio_df, start_date_obj, base_currency
            )

        if result is None or result[0] is None:

            # 실패한 티커 정보 추출
            failed_tickers = result[5] if result and len(result) > 5 else []

            error_msg = "포트폴리오 데이터를 가져올 수 없습니다."
            if failed_tickers:
                error_msg += (
                    f" 다음 티커에 문제가 있습니다: {', '.join(failed_tickers)}"
                )
            else:
                error_msg += " 가능한 원인: 1) 모든 티커가 유효하지 않음, 2) 시작 날짜가 너무 최근, 3) 네트워크 오류"

            return jsonify({"error": error_msg}), 400

        (
            portfolio_returns,
            portfolio_series,
            portfolio_data,
            cash_holdings,
            total_initial_value_with_cash,
            failed_tickers,  # 실패한 티커 리스트 받기
            has_dca,  # DCA 사용 여부
        ) = result

        # 일부 티커가 실패한 경우 경고 메시지 추가
        warning_msg = None
        if failed_tickers:
            warning_msg = f"⚠️ 다음 티커의 데이터를 가져올 수 없어 제외되었습니다: {', '.join(failed_tickers)}"
            app.logger.warning(f"⚠️ Warning: Some tickers failed: {failed_tickers}")

        # 벤치마크 데이터 가져오기
        benchmark_returns = None
        benchmark_name = benchmark_ticker  # 표시용 이름

        # 헤지펀드 벤치마크인지 확인
        if benchmark_ticker.startswith("HEDGEFUND_"):
            try:
                app.logger.info(f"🏢 헤지펀드 벤치마크 선택: {benchmark_ticker}")
                benchmark_returns = calculate_hedgefund_benchmark_returns(
                    benchmark_ticker, start_date_obj, base_currency
                )
                benchmark_name = HEDGEFUND_BENCHMARKS[benchmark_ticker]["name"]
                app.logger.info(f"✅ 헤지펀드 벤치마크 로드 완료: {benchmark_name}")
            except Exception as e:
                app.logger.error(f"❌ 헤지펀드 벤치마크 계산 실패: {e}")
                return (
                    jsonify({"error": f"헤지펀드 벤치마크 계산 중 오류: {str(e)}"}),
                    400,
                )
        else:
            # 일반 티커 벤치마크
            app.logger.info(f"📊 Fetching benchmark ticker: {benchmark_ticker}")
            benchmark_data = fetch_stock_data(
                benchmark_ticker, start_date_obj, datetime.now()
            )

            if benchmark_data is None:
                app.logger.error(
                    f"❌ Failed to fetch benchmark data for {benchmark_ticker}"
                )
                return (
                    jsonify(
                        {
                            "error": f'벤치마크 티커 "{benchmark_ticker}"의 데이터를 가져올 수 없습니다.\n'
                            f"가능한 원인:\n"
                            f"1) 티커 심볼이 잘못되었습니다 (예: VOO, SPY, QQQ 등 확인)\n"
                            f"2) Yahoo Finance API 일시적 오류 (잠시 후 다시 시도)\n"
                            f"3) 네트워크 연결 문제\n"
                            f"4) 해당 종목이 상장폐지되었을 수 있습니다"
                        }
                    ),
                    500,
                )

            app.logger.info(
                f"✅ Benchmark data fetched: {len(benchmark_data)} data points"
            )

            # 벤치마크 데이터도 fill_missing_dates 호출
            app.logger.info(f"🔄 Filling missing dates for benchmark...")
            benchmark_data = fill_missing_dates(
                benchmark_data, start_date_obj, datetime.now()
            )

            if benchmark_data is None or len(benchmark_data) == 0:
                app.logger.warning(
                    f"❌ Failed to process benchmark data for {benchmark_ticker}"
                )
                return (
                    jsonify({"error": f"벤치마크 데이터 처리 중 오류가 발생했습니다."}),
                    400,
                )

            # 벤치마크 수익률 계산
            benchmark_returns = benchmark_data.pct_change().dropna()

        # 지표 계산
        metrics = calculate_metrics(portfolio_returns, benchmark_returns)

        if metrics is None:
            app.logger.warning(f"❌ calculate_metrics returned None")
            return (
                jsonify(
                    {
                        "error": "지표를 계산할 수 없습니다. 포트폴리오와 벤치마크의 날짜 범위가 겹치지 않습니다."
                    }
                ),
                400,
            )

        # 차트 데이터 준비
        chart_data = prepare_chart_data(
            portfolio_returns, benchmark_returns, portfolio_series
        )

        # 현재 환율 정보 (보유 종목 테이블과 요약에 사용)
        exchange_rate = get_current_exchange_rate()

        # 도넛 차트 데이터 준비
        allocation_data = prepare_allocation_data(
            portfolio_data, cash_holdings, total_initial_value_with_cash
        )

        # 보유 종목 테이블 데이터 준비
        holdings_table = prepare_holdings_table(
            portfolio_data, cash_holdings, base_currency, exchange_rate
        )

        # 포트폴리오 요약 정보
        current_value = portfolio_series.iloc[-1]

        # DCA가 있는 경우 초기값은 첫날 가치가 아니라 첫 투자 금액 사용
        if has_dca:
            # 첫 투자 시점의 투자 금액이 초기값
            # total_initial_value_with_cash - 현금 = 투자 자산 초기값
            initial_value = total_initial_value_with_cash - sum(
                cash["value"] for cash in cash_holdings.values()
            )
        else:
            # 일반 포트폴리오는 첫날 가치
            initial_value = portfolio_series.iloc[0]

        # 현금 총액 계산
        total_cash = sum(cash["value"] for cash in cash_holdings.values())

        # 현금 포함한 현재 총 가치
        current_value_with_cash = current_value + total_cash
        initial_value_with_cash = total_initial_value_with_cash

        summary = {
            "initial_value": round(initial_value, 2),
            "current_value": round(current_value, 2),
            "initial_value_with_cash": round(initial_value_with_cash, 2),
            "current_value_with_cash": round(current_value_with_cash, 2),
            "total_cash": round(total_cash, 2),
            "total_return": (
                round((current_value / initial_value - 1) * 100, 2)
                if initial_value > 0
                else 0
            ),
            "total_return_with_cash": (
                round((current_value_with_cash / initial_value_with_cash - 1) * 100, 2)
                if initial_value_with_cash > 0
                else 0
            ),
            "start_date": start_date,
            "end_date": datetime.now().strftime("%Y-%m-%d"),
            "benchmark": benchmark_ticker,
            "benchmark_name": benchmark_name,  # 표시용 벤치마크 이름 추가
            "num_holdings": len(portfolio_data),
            "base_currency": base_currency,
            "exchange_rate": round(exchange_rate, 2),
        }

        # 최종 포트폴리오를 CSV 형식으로 변환 (DCA 적용 후의 실제 보유량)
        final_portfolio_rows = []
        for ticker, data in portfolio_data.items():
            final_portfolio_rows.append(
                {
                    "티커": ticker,
                    "종목명": data.get("name", ""),
                    "보유량": data["quantity"],
                    "국가": data.get("country", "미국"),
                    "분류": "주식",
                }
            )

        # 현금 추가
        for ticker, cash_data in cash_holdings.items():
            final_portfolio_rows.append(
                {
                    "티커": ticker,
                    "종목명": f"현금 ({cash_data['country']})",
                    "보유량": cash_data["value"],
                    "국가": cash_data["country"],
                    "분류": "현금",
                }
            )

        final_portfolio_df = pd.DataFrame(final_portfolio_rows)
        final_portfolio_csv = final_portfolio_df.to_csv(index=False)

        return jsonify(
            {
                "metrics": metrics,
                "chart_data": chart_data,
                "summary": summary,
                "allocation_data": allocation_data,
                "holdings_table": holdings_table,
                "warning": warning_msg,  # 경고 메시지 추가
                "final_portfolio_csv": final_portfolio_csv,  # 최종 포트폴리오 CSV 추가
            }
        )

    except Exception as e:
        error_trace = traceback.format_exc()
        app.logger.warning("=" * 80)
        app.logger.warning("❌ ERROR in /analyze endpoint:")
        app.logger.warning(error_trace)
        app.logger.warning("=" * 80)
        return (
            jsonify(
                {
                    "error": f"분석 중 오류가 발생했습니다: {str(e)}\n\n서버 터미널에서 상세 로그를 확인하세요."
                }
            ),
            500,
        )


@app.route("/api/ai-analysis", methods=["POST"])
def ai_analysis():
    """OpenAI를 사용한 포트폴리오 AI 분석"""
    try:
        # 로그인 체크 - 필수
        if "user_id" not in session:
            return (
                jsonify({"success": False, "error": "로그인이 필요한 기능입니다."}),
                401,
            )

        import json
        from datetime import datetime, timedelta

        # 세션에서 user_id 가져오기 (user_id 기반 rate limiting)
        user_id = session.get("user_id")

        current_time = datetime.now()

        # Rate limiting 체크 (1분에 1번) - user_id 기반
        if user_id in ai_analysis_rate_limit:
            last_request = ai_analysis_rate_limit[user_id]
            time_diff = (current_time - last_request).total_seconds()

            if time_diff < 60:  # 60초 = 1분
                remaining_seconds = int(60 - time_diff)
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"AI 분석은 1분에 1번만 가능합니다. {remaining_seconds}초 후에 다시 시도해주세요.",
                            "rate_limited": True,
                            "remaining_seconds": remaining_seconds,
                        }
                    ),
                    429,
                )

        data: dict = request.json

        # 필요한 데이터 추출
        holdings: list = data.get("holdings", [])
        metrics: dict = data.get("metrics", {})
        summary: dict = data.get("summary", {})
        benchmark: str = summary.get("benchmark", "Unknown")

        # 캐시 키 생성 (holdings의 티커와 비중으로)
        cache_key = json.dumps(
            {
                "holdings": sorted([(h["ticker"], h["weight"]) for h in holdings]),
                "cagr": metrics.get("cagr"),
                "sharpe": metrics.get("sharpe_ratio"),
                "benchmark": benchmark,
            },
            sort_keys=True,
        )

        # 캐시에서 확인 (같은 포트폴리오는 재분석하지 않음) - user_id 기반
        if user_id in ai_analysis_cache:
            cached_data = ai_analysis_cache[user_id]
            if cached_data.get("cache_key") == cache_key:
                app.logger.info(
                    f"✅ Returning cached AI analysis for user_id: {user_id}"
                )
                return jsonify(
                    {"success": True, "analysis": cached_data["result"], "cached": True}
                )

        # 벤치마크 이름 매핑
        benchmark_names = {
            "SPY": "S&P 500",
            "^GSPC": "S&P 500",
            "QQQ": "NASDAQ 100",
            "^NDX": "NASDAQ 100",
            "069500.KS": "KOSPI 200",
        }
        benchmark_name = benchmark_names.get(benchmark, benchmark)

        # 보유 종목 정보 포맷팅
        holdings_text = "\n".join(
            [f"- {h['ticker']} ({h['name']}): {h['weight']}%" for h in holdings]
        )

        # 프롬프트 구성
        prompt = f"""
        You are a professional portfolio analyst. Analyze the following portfolio and produce a structured Korean report.

        ### Portfolio Holdings
        {holdings_text}

        ### Performance Metrics
        - CAGR: {metrics.get('cagr', 'N/A')}%
        - Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A')}
        - Sortino Ratio: {metrics.get('sortino_ratio', 'N/A')}
        - Alpha: {metrics.get('alpha', 'N/A')}%
        - Beta: {metrics.get('beta', 'N/A')}
        - Volatility: {metrics.get('volatility', 'N/A')}%
        - Max Drawdown (MDD): {metrics.get('max_drawdown', 'N/A')}%

        ### Benchmark ({benchmark_name})
        - Benchmark CAGR: {metrics.get('benchmark_annual_return', 'N/A')}%
        - Benchmark Sharpe: {metrics.get('benchmark_sharpe_ratio', 'N/A')}
        - Benchmark Sortino: {metrics.get('benchmark_sortino_ratio', 'N/A')}
        - Benchmark Volatility: {metrics.get('benchmark_volatility', 'N/A')}%

        ### Output Requirements
        - **Write the response only in Korean**
        - **Do not include any introductory phrases such as "Certainly", "Here is", or similar**
        - Format in **Markdown**
        - Maintain a professional, direct, and objective tone
        - Use appropriate emojis to improve readability
        - The analysis must have exactly three sections with `##` headers:

        1. **포트폴리오 강점 분석**
        - 벤치마크 대비 강점
        - 위험 대비 성과가 좋은 이유
        - 구성 측면의 장점

        2. **포트폴리오 약점 및 위험 요소**
        - 부족한 지표
        - 잠재적 리스크
        - 벤치마크 대비 취약 지점

        3. **개선 제안**
        - 실행 가능한 개선 전략
        - 리밸런싱 제안
        - 편입/제외 고려 종목

        Respond in a clear, highly analytical style, with actionable insights and no unnecessary sentences.
        """

        # OpenAI API 호출
        app.logger.info("🤖 Calling OpenAI API...")

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 20년 경력의 전문 포트폴리오 분석가입니다. 데이터 기반으로 객관적이고 실용적인 조언을 제공합니다.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
        )

        analysis_result = response.choices[0].message.content

        app.logger.info("✅ OpenAI API call successful")

        # Rate limit 업데이트 (user_id 기반)
        ai_analysis_rate_limit[user_id] = current_time

        # 캐시 저장 (user_id 기반)
        ai_analysis_cache[user_id] = {
            "cache_key": cache_key,
            "result": analysis_result,
            "timestamp": current_time,
        }

        return jsonify({"success": True, "analysis": analysis_result, "cached": False})

    except Exception as e:
        error_trace = traceback.format_exc()
        app.logger.warning("❌ ERROR in /api/ai-analysis endpoint:")
        app.logger.warning(error_trace)
        return (
            jsonify(
                {"success": False, "error": f"AI 분석 중 오류가 발생했습니다: {str(e)}"}
            ),
            500,
        )


if __name__ == "__main__":
    # 데이터베이스 초기화
    init_database()

    # Flask 앱 실행 (외부 접속 허용)
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", debug=True, port=port)
