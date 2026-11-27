#!/bin/sh
# Fetch only the Rocketbox avatars and poses used here (MIT licence; github.com/microsoft/Microsoft-Rocketbox).
# The BRAS CR3 photo (CR3 medium room/Pictures/CR3_360panorama.jpg) is copied by hand next to these scripts.
set -e
cd "$(dirname "$0")"
[ -d microsoft-rocketbox ] || GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --filter=blob:none --no-checkout https://github.com/microsoft/microsoft-rocketbox
cd microsoft-rocketbox
git sparse-checkout init --no-cone
git sparse-checkout set \
  '/Assets/Avatars/Professions/Business_Male_01/' '/Assets/Avatars/Professions/Business_Male_02/' \
  '/Assets/Avatars/Professions/Business_Male_03/' '/Assets/Avatars/Professions/Business_Male_05/' \
  '/Assets/Avatars/Professions/Business_Male_06/' '/Assets/Avatars/Professions/Business_Female_01/' \
  '/Assets/Avatars/Professions/Business_Female_04/' \
  '/Assets/Animations/all_animations_max_motextr_static/m_sit_chair_idle_neutral_01.max.fbx' \
  '/Assets/Animations/all_animations_max_motextr_static/f_sit_chair_idle_neutral_01.max.fbx' \
  '/Assets/Animations/all_animations_max_motextr_static/m_idle_neutral_01.max.fbx' \
  '/Assets/Animations/all_animations_max_motextr_static/f_idle_neutral_01.max.fbx'
git checkout -q HEAD
