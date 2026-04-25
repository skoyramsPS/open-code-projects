from __future__ import annotations


def test_target_tree_wrappers_point_to_moved_image_helper_modules() -> None:
    import comicbook.image_client as wrapped_image_client
    import comicbook.input_file as wrapped_input_file
    import comicbook.metadata_prompts as wrapped_metadata_prompts
    import comicbook.router_llm as wrapped_router_llm
    import comicbook.router_prompts as wrapped_router_prompts
    from pipelines.workflows.image_prompt_gen import input_file as moved_input_file
    from pipelines.workflows.image_prompt_gen.adapters import image_client as moved_image_client
    from pipelines.workflows.image_prompt_gen.adapters import router_llm as moved_router_llm
    from pipelines.workflows.image_prompt_gen.prompts import metadata_prompts as moved_metadata_prompts
    from pipelines.workflows.image_prompt_gen.prompts import router_prompts as moved_router_prompts

    assert wrapped_input_file is moved_input_file
    assert wrapped_router_prompts is moved_router_prompts
    assert wrapped_metadata_prompts is moved_metadata_prompts
    assert wrapped_router_llm is moved_router_llm
    assert wrapped_image_client is moved_image_client


def test_image_run_module_uses_moved_input_file_module() -> None:
    from pipelines.workflows.image_prompt_gen import input_file as input_file_module
    from pipelines.workflows.image_prompt_gen import run as run_module

    assert run_module.InputFileValidationError is input_file_module.InputFileValidationError
    assert run_module.InputPromptRecord is input_file_module.InputPromptRecord
    assert run_module.load_input_records is input_file_module.load_input_records
