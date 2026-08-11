from __future__ import annotations

from io import BytesIO
from math import isnan
from numbers import Number
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
from authlib.integrations.flask_client import OAuth
from bokeh.embed import components
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.palettes import Category10
from bokeh.plotting import figure
from flask import (
    Flask,
    Response,
    abort,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.middleware.proxy_fix import ProxyFix

from oilgas.config import settings
from oilgas.web.auth import authentication_settings
from oilgas.web.filters import ReportFilters
from oilgas.web.reports import ReportRepository


def create_app(database_path: Path | None = None) -> Flask:
    """Create the read-only local reporting application."""
    path = database_path or settings.database
    repository = ReportRepository(path)
    auth = authentication_settings()
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_proto=1)
    app.config.update(
        DATABASE_PATH=path,
        SECRET_KEY=auth.secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=auth.required,
        PERMANENT_SESSION_LIFETIME=43200,
    )

    google = None
    if auth.required:
        oauth = OAuth(app)
        google = oauth.register(
            name="google",
            client_id=auth.google_client_id,
            client_secret=auth.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    @app.before_request
    def require_login():
        if not auth.required or request.endpoint in {"login", "google_callback", "static"}:
            return None
        if session.get("email"):
            return None
        return redirect(url_for("login"))

    @app.get("/login")
    def login():
        if not auth.required:
            return redirect(url_for("index"))
        if session.get("email"):
            return redirect(url_for("index"))
        assert google is not None
        return google.authorize_redirect(url_for("google_callback", _external=True))

    @app.get("/auth/google/callback")
    def google_callback():
        assert google is not None
        token = google.authorize_access_token()
        userinfo = token.get("userinfo") or google.get("userinfo").json()
        email = str(userinfo.get("email", "")).casefold()
        if not userinfo.get("email_verified") or email not in auth.allowed_emails:
            session.clear()
            abort(403, "Your Google account is not approved for this application.")
        session.clear()
        session["email"] = email
        session["name"] = userinfo.get("name", email)
        session.permanent = True
        return redirect(url_for("index"))

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login" if auth.required else "index"))

    @app.template_filter("display_value")
    def display_value(value: object, column: str) -> str:
        if value is None or pd.isna(value):
            return "--"
        if isinstance(value, Number) and not isinstance(value, bool):
            if isinstance(value, float) and isnan(value):
                return "--"
            if "price" in column:
                return f"{value:,.4f}"
            if "interest" in column or "percent" in column:
                return f"{value:,.8f}"
            if "volume" in column:
                return f"{value:,.3f}"
            if "count" in column or isinstance(value, int):
                return f"{value:,}"
            return f"{value:,.2f}"
        return str(value)

    @app.context_processor
    def template_context():
        def cashflow_detail_url(report_month: object) -> str:
            query = request.args.to_dict(flat=False)
            month = pd.Timestamp(report_month).strftime("%Y-%m")
            query["start_month"] = [month]
            query["end_month"] = [month]
            return f"/cashflow/details?{urlencode(query, doseq=True)}"

        def detail_audit_url(row: dict[str, object]) -> str:
            query = request.args.to_dict(flat=False)
            month = pd.Timestamp(row["report_month"]).strftime("%Y-%m")
            query["start_month"] = [month]
            query["end_month"] = [month]
            query["operator"] = [str(row["operator_name"])]
            if row["record_type"] == "revenue":
                query["property"] = [str(row["property_name"])]
                return f"/audit/revenue?{urlencode(query, doseq=True)}"
            query["cost_center"] = [str(row["cost_center_code"])]
            return f"/audit/jib?{urlencode(query, doseq=True)}"

        return {
            "filter_options": repository.filter_options(),
            "auth_required": auth.required,
            "current_user_name": session.get("name"),
            "cashflow_detail_url": cashflow_detail_url,
            "detail_audit_url": detail_audit_url,
        }

    @app.get("/")
    def index():
        filters = ReportFilters.from_request(request)
        data = repository.overview(filters)
        summary = _summary(data)
        return render_report(
            title="Cashflow overview",
            report_name="cashflow",
            filters=filters,
            data=data,
            chart=_cashflow_chart(data, cumulative=filters.cumulative, rollup=filters.rollup),
            summary=summary,
            date_note="Revenue and JIB date bases are independently selectable.",
        )

    @app.get("/cashflow")
    def cashflow():
        filters = ReportFilters.from_request(request)
        data = repository.cashflow_rollup(filters)
        return render_report(
            title="Revenue, JIB expense, and net cashflow",
            report_name="cashflow",
            filters=filters,
            data=data,
            chart=_cashflow_chart(data, cumulative=filters.cumulative, rollup=filters.rollup),
            summary=_summary(data),
            date_note=(
                "Monthly totals are unallocated. Select a month to drill into "
                "revenue properties and JIB cost centers."
            ),
        )

    @app.get("/cashflow/details")
    def cashflow_details():
        filters = ReportFilters.from_request(request)
        data = repository.cashflow_details(filters)
        return render_report(
            title="Cashflow detail",
            report_name="cashflow_details",
            filters=filters,
            data=data,
            chart=None,
            summary=_summary(data),
            date_note=(
                "Revenue properties and JIB cost centers are shown independently; "
                "no expense allocation is applied."
            ),
        )

    @app.get("/production")
    def production():
        filters = ReportFilters.from_request(request)
        data = repository.production_history(filters)
        return render_report(
            title="Production history",
            report_name="production",
            filters=filters,
            data=data,
            chart=_production_chart(data, cumulative=filters.cumulative),
            summary=_summary(data),
            date_note=(
                "Property gross volume/value and recorded owner volume/net value "
                "are shown separately."
            ),
        )

    @app.get("/prices")
    def prices():
        filters = ReportFilters.from_request(request)
        data = repository.price_history(filters)
        return render_report(
            title="Price history",
            report_name="prices",
            filters=filters,
            data=data,
            chart=_price_chart(data),
            summary=_summary(data),
            date_note=(
                "Simple average source unit price by production/check month; "
                "non-positive prices and volumes are excluded."
            ),
        )

    @app.get("/audit/revenue")
    def audit_revenue():
        filters = ReportFilters.from_request(request)
        return render_audit(
            title="Revenue line audit",
            report_name="revenue_lines",
            filters=filters,
            data=repository.revenue_lines(filters),
        )

    @app.get("/audit/jib")
    def audit_jib():
        filters = ReportFilters.from_request(request)
        return render_audit(
            title="JIB line audit",
            report_name="jib_lines",
            filters=filters,
            data=repository.jib_lines(filters),
        )

    @app.get("/export/<report_name>.<file_format>")
    def export(report_name: str, file_format: str):
        filters = ReportFilters.from_request(request)
        data = _report_data(repository, report_name, filters)
        if file_format == "csv":
            return Response(
                data.to_csv(index=False),
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment; filename={report_name}.csv"},
            )
        if file_format == "xlsx":
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                data.to_excel(writer, sheet_name=report_name[:31], index=False)
                metadata = pd.DataFrame(
                    [(key, value) for key, value in request.args.items(multi=True)],
                    columns=["filter", "value"],
                )
                metadata.to_excel(writer, sheet_name="report_filters", index=False)
            output.seek(0)
            return send_file(
                output,
                as_attachment=True,
                download_name=f"{report_name}.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        abort(404)

    @app.get("/source/<source_file_id>")
    def source_document(source_file_id: str):
        source = repository.source_path(source_file_id)
        if source is None or not source.is_file():
            abort(404, "Source PDF is unavailable. Sync the raw PDF directory to this machine.")
        return send_file(source, mimetype="application/pdf", download_name=source.name)

    def render_report(
        title: str,
        report_name: str,
        filters: ReportFilters,
        data: pd.DataFrame,
        chart: tuple[str, str] | None,
        summary: dict[str, str],
        date_note: str,
    ):
        script, div = chart or (None, None)
        return render_template(
            "report.html",
            title=title,
            report_name=report_name,
            filters=filters,
            rows=_records(data),
            columns=_display_columns(data, report_name, filters),
            numeric_columns=_numeric_columns(data),
            drilldown_months=report_name == "cashflow" and filters.rollup == "monthly",
            drilldown_audits=report_name == "cashflow_details",
            cumulative_supported=report_name in {"cashflow", "production"},
            chart_value_period=filters.rollup if report_name == "cashflow" else "monthly",
            rollup_supported=report_name == "cashflow",
            chart_script=script,
            chart_div=div,
            summary=summary,
            date_note=date_note,
        )

    def render_audit(title: str, report_name: str, filters: ReportFilters, data: pd.DataFrame):
        return render_template(
            "audit.html",
            title=title,
            report_name=report_name,
            filters=filters,
            rows=_records(data),
            columns=list(data.columns),
            numeric_columns=_numeric_columns(data),
        )

    return app


def _report_data(
    repository: ReportRepository, report_name: str, filters: ReportFilters
) -> pd.DataFrame:
    reports = {
        "cashflow": repository.cashflow_rollup,
        "cashflow_details": repository.cashflow_details,
        "production": repository.production_history,
        "prices": repository.price_history,
        "revenue_lines": repository.revenue_lines,
        "jib_lines": repository.jib_lines,
    }
    report = reports.get(report_name)
    if report is None:
        abort(404)
    return report(filters)


def _records(data: pd.DataFrame) -> list[dict[str, object]]:
    display = data.copy()
    for column in display.columns:
        if pd.api.types.is_datetime64_any_dtype(display[column]):
            display[column] = display[column].dt.strftime("%Y-%m-%d")
    return display.where(pd.notnull(display), None).to_dict(orient="records")


def _display_columns(data: pd.DataFrame, report_name: str, filters: ReportFilters) -> list[str]:
    columns = list(data.columns)
    if report_name == "cashflow" and filters.rollup != "monthly" and "report_period" in columns:
        columns.remove("report_month")
        columns.insert(0, columns.pop(columns.index("report_period")))
    return columns


def _numeric_columns(data: pd.DataFrame) -> set[str]:
    return {
        column
        for column in data.columns
        if pd.api.types.is_numeric_dtype(data[column]) and column != "source_file_id"
    }


def _summary(data: pd.DataFrame) -> dict[str, str]:
    totals: dict[str, str] = {"rows": f"{len(data):,}"}
    for column in ("revenue_net", "jib_expense", "net_cashflow", "property_volume", "owner_volume"):
        if column in data:
            totals[column.replace("_", " ")] = f"{data[column].fillna(0).sum():,.2f}"
    return totals


def _date_range_label(data: pd.DataFrame) -> str:
    dates = pd.to_datetime(data["report_month"])
    first, last = dates.min(), dates.max()
    if first == last:
        return first.strftime("%b %Y")
    return f"{first:%b %Y} – {last:%b %Y}"


def _cashflow_chart(data: pd.DataFrame, cumulative: bool, rollup: str) -> tuple[str, str] | None:
    if data.empty:
        return None
    group_columns = ["report_month"]
    if "report_period" in data:
        group_columns.append("report_period")
    monthly = data.groupby(group_columns, as_index=False)[
        ["revenue_net", "jib_expense", "net_cashflow"]
    ].sum()
    monthly = monthly.sort_values("report_month")
    if cumulative:
        monthly[["revenue_net", "jib_expense", "net_cashflow"]] = monthly[
            ["revenue_net", "jib_expense", "net_cashflow"]
        ].cumsum()
    rollup_label = rollup.capitalize()
    chart_label = f"{rollup_label} cashflow"
    if cumulative:
        chart_label = f"Cumulative {chart_label.lower()}"
    chart_label = f"{chart_label} · {_date_range_label(monthly)}"

    x_field = "report_month"
    figure_options: dict[str, object] = {"x_axis_type": "datetime"}
    if rollup != "monthly":
        x_field = "report_period"
        figure_options = {"x_range": monthly["report_period"].tolist()}

    plot = figure(
        height=360,
        title=chart_label,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
        **figure_options,
    )
    colors = {"revenue_net": "#2f7d4a", "jib_expense": "#b7472a", "net_cashflow": "#2b5c9b"}
    for field, label in (
        ("revenue_net", "Revenue"),
        ("jib_expense", "JIB expense"),
        ("net_cashflow", "Net cashflow"),
    ):
        source_columns = [x_field, field]
        source = ColumnDataSource(monthly[source_columns].rename(columns={field: "amount"}))
        plot.line(
            x_field,
            "amount",
            source=source,
            line_width=3,
            color=colors[field],
            legend_label=label,
        )
        plot.scatter(x_field, "amount", source=source, size=6, color=colors[field])
    tooltip_label = "Period" if rollup != "monthly" else "Month"
    tooltip_value = f"@{x_field}"
    formatters = {"@report_month": "datetime"} if rollup == "monthly" else {}
    if rollup == "monthly":
        tooltip_value = "@report_month{%F}"
    plot.add_tools(
        HoverTool(
            tooltips=[(tooltip_label, tooltip_value), ("Amount", "@amount{$0,0.00}")],
            formatters=formatters,
        )
    )
    plot.legend.click_policy = "hide"
    return components(plot)


def _production_chart(data: pd.DataFrame, cumulative: bool) -> tuple[str, str] | None:
    if data.empty:
        return None
    monthly = data.groupby(["report_month", "product"], as_index=False)["property_volume"].sum()
    monthly = monthly.sort_values(["product", "report_month"])
    if cumulative:
        monthly["property_volume"] = monthly.groupby("product")["property_volume"].cumsum()
    chart_label = "Cumulative property gross volume" if cumulative else "Property gross volume"
    chart_label = f"{chart_label} · {_date_range_label(monthly)}"
    plot = figure(
        height=360,
        x_axis_type="datetime",
        title=chart_label,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    for index, product in enumerate(monthly["product"].unique()):
        series = monthly[monthly["product"] == product]
        plot.line(
            "report_month",
            "property_volume",
            source=ColumnDataSource(series),
            line_width=3,
            color=Category10[10][index % 10],
            legend_label=product,
        )
    plot.add_tools(
        HoverTool(
            tooltips=[
                ("Month", "@report_month{%F}"),
                ("Volume", "@property_volume{0,0.00}"),
                ("Product", "@product"),
            ],
            formatters={"@report_month": "datetime"},
        )
    )
    plot.legend.click_policy = "hide"
    return components(plot)


def _price_chart(data: pd.DataFrame) -> tuple[str, str] | None:
    if data.empty:
        return None
    monthly = data.groupby(["report_month", "product"], as_index=False)["average_unit_price"].mean()
    plot = figure(
        height=360,
        x_axis_type="datetime",
        title=f"Average unit price · {_date_range_label(monthly)}",
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    for index, product in enumerate(monthly["product"].unique()):
        series = monthly[monthly["product"] == product]
        plot.line(
            "report_month",
            "average_unit_price",
            source=ColumnDataSource(series),
            line_width=3,
            color=Category10[10][index % 10],
            legend_label=product,
        )
    plot.add_tools(
        HoverTool(
            tooltips=[
                ("Month", "@report_month{%F}"),
                ("Price", "@average_unit_price{$0,0.0000}"),
                ("Product", "@product"),
            ],
            formatters={"@report_month": "datetime"},
        )
    )
    plot.legend.click_policy = "hide"
    return components(plot)
