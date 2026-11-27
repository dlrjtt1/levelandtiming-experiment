import unreal
ok = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log(f"[CR3] saved: {ok}")
unreal.SystemLibrary.quit_editor()
