from __future__ import annotations


def test_target_tree_compat_package_no_longer_uses_legacy_package_path_fallback() -> None:
    import comicbook

    assert all(not path.endswith("ComicBook/comicbook") for path in comicbook.__path__)


def test_target_tree_state_wrapper_reexports_split_state_symbols() -> None:
    import comicbook.state as wrapped_state_module
    from pipelines.shared import state as shared_state_module
    from pipelines.workflows.image_prompt_gen import state as image_state_module
    from pipelines.workflows.template_upload import state as upload_state_module

    assert wrapped_state_module.TemplateSummary is image_state_module.TemplateSummary
    assert wrapped_state_module.RunState is image_state_module.RunState
    assert wrapped_state_module.ImportRunState is upload_state_module.ImportRunState
    assert wrapped_state_module.WorkflowError is shared_state_module.WorkflowError


def test_target_tree_compat_node_package_imports_without_legacy_path_fallback() -> None:
    import comicbook
    import comicbook.nodes

    assert all(not path.endswith("ComicBook/comicbook") for path in comicbook.__path__)
    assert comicbook.nodes.__doc__


def test_moved_image_node_wrappers_point_to_target_tree_modules() -> None:
    import comicbook.nodes.cache_lookup as wrapped_cache_lookup_module
    import comicbook.nodes.generate_images_serial as wrapped_generate_images_serial_module
    import comicbook.nodes.ingest as wrapped_ingest_module
    import comicbook.nodes.load_templates as wrapped_load_templates_module
    import comicbook.nodes.persist_template as wrapped_persist_template_module
    import comicbook.nodes.router as wrapped_router_module
    import comicbook.nodes.summarize as wrapped_summarize_module
    from pipelines.workflows.image_prompt_gen.nodes import cache_lookup as moved_cache_lookup_module
    from pipelines.workflows.image_prompt_gen.nodes import generate_images_serial as moved_generate_images_serial_module
    from pipelines.workflows.image_prompt_gen.nodes import ingest as moved_ingest_module
    from pipelines.workflows.image_prompt_gen.nodes import load_templates as moved_load_templates_module
    from pipelines.workflows.image_prompt_gen.nodes import persist_template as moved_persist_template_module
    from pipelines.workflows.image_prompt_gen.nodes import router as moved_router_module
    from pipelines.workflows.image_prompt_gen.nodes import summarize as moved_summarize_module

    assert wrapped_cache_lookup_module is moved_cache_lookup_module
    assert wrapped_cache_lookup_module.cache_lookup is moved_cache_lookup_module.cache_lookup
    assert wrapped_generate_images_serial_module is moved_generate_images_serial_module
    assert wrapped_generate_images_serial_module.generate_images_serial is moved_generate_images_serial_module.generate_images_serial
    assert wrapped_ingest_module is moved_ingest_module
    assert wrapped_ingest_module.ingest is moved_ingest_module.ingest
    assert wrapped_load_templates_module is moved_load_templates_module
    assert wrapped_load_templates_module.load_templates is moved_load_templates_module.load_templates
    assert wrapped_persist_template_module is moved_persist_template_module
    assert wrapped_persist_template_module.persist_template is moved_persist_template_module.persist_template
    assert wrapped_router_module is moved_router_module
    assert wrapped_router_module.router is moved_router_module.router
    assert wrapped_summarize_module is moved_summarize_module
    assert wrapped_summarize_module.summarize is moved_summarize_module.summarize


def test_moved_graph_modules_import_with_explicit_state_and_node_wrappers() -> None:
    import comicbook
    from pipelines.workflows.image_prompt_gen import graph as image_graph_module
    from pipelines.workflows.template_upload import graph as upload_graph_module

    assert all(not path.endswith("ComicBook/comicbook") for path in comicbook.__path__)
    assert callable(image_graph_module.build_workflow_graph)
    assert callable(upload_graph_module.build_upload_graph)


def test_moved_template_upload_preflight_node_wrappers_point_to_target_tree_modules() -> None:
    import comicbook.nodes.upload_backfill_metadata as wrapped_upload_backfill_metadata_module
    import comicbook.nodes.upload_decide_write_mode as wrapped_upload_decide_write_mode_module
    import comicbook.nodes.upload_load_file as wrapped_upload_load_file_module
    import comicbook.nodes.upload_parse_and_validate as wrapped_upload_parse_and_validate_module
    import comicbook.nodes.upload_persist as wrapped_upload_persist_module
    import comicbook.nodes.upload_resume_filter as wrapped_upload_resume_filter_module
    import comicbook.nodes.upload_summarize as wrapped_upload_summarize_module
    from pipelines.workflows.template_upload.nodes import backfill_metadata as moved_backfill_metadata_module
    from pipelines.workflows.template_upload.nodes import decide_write_mode as moved_decide_write_mode_module
    from pipelines.workflows.template_upload.nodes import load_file as moved_load_file_module
    from pipelines.workflows.template_upload.nodes import parse_and_validate as moved_parse_and_validate_module
    from pipelines.workflows.template_upload.nodes import persist as moved_persist_module
    from pipelines.workflows.template_upload.nodes import resume_filter as moved_resume_filter_module
    from pipelines.workflows.template_upload.nodes import summarize as moved_summarize_module

    assert wrapped_upload_backfill_metadata_module.upload_backfill_metadata is moved_backfill_metadata_module.backfill_metadata
    assert wrapped_upload_load_file_module.upload_load_file is moved_load_file_module.load_file
    assert wrapped_upload_parse_and_validate_module.upload_parse_and_validate is moved_parse_and_validate_module.parse_and_validate
    assert wrapped_upload_resume_filter_module.upload_resume_filter is moved_resume_filter_module.resume_filter
    assert wrapped_upload_decide_write_mode_module.upload_decide_write_mode is moved_decide_write_mode_module.decide_write_mode
    assert wrapped_upload_persist_module.upload_persist is moved_persist_module.persist
    assert wrapped_upload_summarize_module.upload_summarize is moved_summarize_module.summarize
