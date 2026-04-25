from __future__ import annotations


def test_target_tree_compat_package_no_longer_uses_legacy_package_path_fallback() -> None:
    import comicbook

    assert all(not path.endswith("ComicBook/comicbook") for path in comicbook.__path__)


def test_target_tree_state_wrapper_points_to_legacy_state_module() -> None:
    import comicbook.state as wrapped_state_module
    from ComicBook.comicbook import state as legacy_state_module

    assert wrapped_state_module is legacy_state_module
    assert wrapped_state_module.TemplateSummary is legacy_state_module.TemplateSummary
    assert wrapped_state_module.RunState is legacy_state_module.RunState
    assert wrapped_state_module.ImportRunState is legacy_state_module.ImportRunState


def test_target_tree_node_wrappers_point_to_legacy_node_modules() -> None:
    import comicbook.nodes.ingest as wrapped_ingest_module
    import comicbook.nodes.upload_load_file as wrapped_upload_load_file_module
    from ComicBook.comicbook.nodes import ingest as legacy_ingest_module
    from ComicBook.comicbook.nodes import upload_load_file as legacy_upload_load_file_module

    assert wrapped_ingest_module is legacy_ingest_module
    assert wrapped_ingest_module.ingest is legacy_ingest_module.ingest
    assert wrapped_upload_load_file_module is legacy_upload_load_file_module
    assert wrapped_upload_load_file_module.upload_load_file is legacy_upload_load_file_module.upload_load_file


def test_moved_graph_modules_import_with_explicit_state_and_node_wrappers() -> None:
    import comicbook
    from pipelines.workflows.image_prompt_gen import graph as image_graph_module
    from pipelines.workflows.template_upload import graph as upload_graph_module

    assert all(not path.endswith("ComicBook/comicbook") for path in comicbook.__path__)
    assert callable(image_graph_module.build_workflow_graph)
    assert callable(upload_graph_module.build_upload_graph)
