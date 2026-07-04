"""NetLogo controls -> MIR open-core adapter.

This adapter packages parsed NetLogo Interface-tab controls into MIR. It does
not execute NetLogo commands, evaluate expressions, or generate runnable code.
"""
from __future__ import annotations

from abm_auto.ingest.netlogo import (
    NetLogoChooser,
    NetLogoInputBox,
    NetLogoModel,
    NetLogoPlotSpec,
    NetLogoSlider,
    NetLogoSwitch,
)
from abm_auto.mir._schema import MIR, MIRMetadata, MIRRun


def netlogo_model_to_mir(model: NetLogoModel) -> MIR:
    """Map a parsed NetLogo model's controls into MIR run params and metrics."""
    return MIR(
        metadata=MIRMetadata(
            name=model.name,
            description=_description_from_info(model.info_text),
            domain="netlogo",
            provenance={
                "source": "netlogo_controls_to_mir",
                "has_code_text": bool(model.code_text),
                "has_info_text": bool(model.info_text),
            },
        ),
        run=MIRRun(seed=0, params=_params_from_model(model)),
        metrics=_metrics_from_model(model),
        trace={
            "source_format": "netlogo",
            "controls": model.controls.to_dict(),
            "legacy_sliders": list(model.sliders),
            "legacy_plots": list(model.plots),
        },
    )


def netlogo_controls_to_mir(model: NetLogoModel) -> MIR:
    """Readable alias for controls-focused call sites."""
    return netlogo_model_to_mir(model)


def _params_from_model(model: NetLogoModel) -> dict:
    params: dict[str, dict] = {}
    for slider in model.controls.sliders:
        params[slider.name] = _slider_param(slider)
    for switch in model.controls.switches:
        params[switch.name] = _switch_param(switch)
    for chooser in model.controls.choosers:
        params[chooser.name] = _chooser_param(chooser)
    for input_box in model.controls.input_boxes:
        params[input_box.name] = _input_box_param(input_box)
    return params


def _slider_param(slider: NetLogoSlider) -> dict:
    return {
        "kind": "slider",
        "label": slider.label,
        "minimum": slider.minimum.to_dict(),
        "maximum": slider.maximum.to_dict(),
        "default": slider.default.to_dict(),
        "step": slider.step.to_dict(),
        "units": slider.units,
        "orientation": slider.orientation,
    }


def _switch_param(switch: NetLogoSwitch) -> dict:
    return {
        "kind": "switch",
        "label": switch.label,
        "default": switch.default,
    }


def _chooser_param(chooser: NetLogoChooser) -> dict:
    return {
        "kind": "chooser",
        "label": chooser.label,
        "choices": list(chooser.choices),
        "default": chooser.default,
    }


def _input_box_param(input_box: NetLogoInputBox) -> dict:
    return {
        "kind": "input_box",
        "label": input_box.label,
        "default": input_box.default.to_dict(),
        "multiline": input_box.multiline,
    }


def _metrics_from_model(model: NetLogoModel) -> list[dict]:
    metrics = [
        {
            "kind": "monitor",
            "name": monitor.name,
            "reporter": monitor.reporter,
        }
        for monitor in model.controls.monitors
    ]
    metrics.extend(_plot_metric(plot) for plot in model.controls.plots)
    return metrics


def _plot_metric(plot: NetLogoPlotSpec) -> dict:
    return {
        "kind": "plot",
        "name": plot.name,
        "x_axis": plot.x_axis,
        "y_axis": plot.y_axis,
        "pens": [
            {
                "name": pen.name,
                "interval": pen.interval.to_dict(),
                "mode": pen.mode,
                "color": pen.color,
                "update_command": pen.update_command,
            }
            for pen in plot.pens
        ],
    }


def _description_from_info(info_text: str) -> str:
    for line in info_text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""
