from __future__ import annotations


def test_image_run_module_uses_moved_input_file_module() -> None:
    from pipelines.workflows.image_prompt_gen import input_file as input_file_module
    from pipelines.workflows.image_prompt_gen import run as run_module

    assert run_module.InputFileValidationError is input_file_module.InputFileValidationError
    assert run_module.InputPromptRecord is input_file_module.InputPromptRecord
    assert run_module.load_input_records is input_file_module.load_input_records
