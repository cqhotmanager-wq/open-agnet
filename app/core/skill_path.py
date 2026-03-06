# 技能目录下路径规范化：避免相对路径中重复 "skills" 导致 .../skills/skills/...


def normalize_relative_to_skill_root(path_str: str) -> str:
    """
    将相对路径规范化为「相对于技能根目录」的形式。
    _BASE_PATH 已是 config.skill.root_path（即 .../skills），
    若传入 "skills/createSkill/SKILL.md" 或 "./skills/createSkill/SKILL.md"
    会变成 .../skills/skills/...，故此处去掉开头的 skills/ 或 ./skills/。
    """
    s = path_str.strip().replace("\\", "/")
    if not s:
        return s
    for prefix in ("./skills/", "skills/", "./", ".\\skills\\", "skills\\"):
        if s.startswith(prefix):
            s = s[len(prefix) :].lstrip("/").lstrip("\\")
            break
    return s
