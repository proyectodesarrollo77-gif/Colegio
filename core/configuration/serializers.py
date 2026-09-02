"""Serializers de configuracion transversal."""
from rest_framework import serializers

from .models import GradeDecimalConfig, ReportHeader, SystemParameter


class ReportHeaderSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source="institution.name", read_only=True)

    class Meta:
        model = ReportHeader
        fields = [
            "id", "institution", "institution_name", "name", "line_1", "line_2", "line_3", "line_4",
            "show_logo", "logo_position", "show_seal", "footer_text", "show_page_numbers",
            "show_print_date", "watermark", "paper_size", "orientation",
            "margin_top", "margin_bottom", "margin_left", "margin_right",
            "is_default", "is_active",
        ]


class GradeDecimalConfigSerializer(serializers.ModelSerializer):
    school_year_name = serializers.CharField(source="school_year.name", read_only=True)
    rounding_display = serializers.CharField(source="get_rounding_mode_display", read_only=True)

    class Meta:
        model = GradeDecimalConfig
        fields = [
            "id", "school_year", "school_year_name", "name", "decimals", "rounding_mode",
            "rounding_display", "round_from", "apply_to_period", "apply_to_area", "apply_to_final",
            "minimum_grade", "maximum_grade", "passing_grade", "is_default", "is_active",
        ]

    def validate(self, attrs):
        minimum = attrs.get("minimum_grade", getattr(self.instance, "minimum_grade", None))
        maximum = attrs.get("maximum_grade", getattr(self.instance, "maximum_grade", None))
        passing = attrs.get("passing_grade", getattr(self.instance, "passing_grade", None))
        if minimum is not None and maximum is not None and minimum >= maximum:
            raise serializers.ValidationError({"maximum_grade": "La nota maxima debe ser mayor que la minima."})
        if passing is not None and minimum is not None and maximum is not None:
            if not (minimum <= passing <= maximum):
                raise serializers.ValidationError(
                    {"passing_grade": "La nota aprobatoria debe estar dentro del rango de la escala."}
                )
        return attrs


class SystemParameterSerializer(serializers.ModelSerializer):
    typed_value = serializers.SerializerMethodField()

    class Meta:
        model = SystemParameter
        fields = [
            "id", "key", "label", "value", "typed_value", "value_type",
            "group", "help_text", "is_editable", "is_active",
        ]

    def get_typed_value(self, obj):
        value = obj.typed_value
        return str(value) if value is not None else None
