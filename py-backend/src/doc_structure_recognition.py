"""
    政策文件条款层级关系识别（最优合并版）

    合并第一版和第二版的所有优势功能：
    - 第一版：图片清理、OCR标题修复、混合结构处理、文件名集成
    - 第二版：全面页码清理、OCR乱码处理、中英文括号支持、二级标题结构

    目标输出结构示例：
    1) 存在章节：
    {
        "title": "...",
        "segments": {
            "第一章": ["第一条 ...", "第二条 ..."],
            "第二章": ["第N条 ..."]
        }
    }

    2) 无章节：
    {
        "title": "...",
        "segments": ["第一条 ...", "第二条 ..."]
    }

    3) 存在章节与节：
    {
        "title": "...",
        "segments": {
            "第一章": {
                "第一节": ["第一条 ...", "第二条 ..."],
                "第二节": []
            }
        }
    }

    4) 三级标题结构：
    {
        "title": "...",
        "segments": {
            "一、标题": {
                "（一）子标题": ["1.内容..", "2.内容.."],
                "（二）子标题": ["内容..."]
            }
        }
    }

    5) 二级标题结构：
    {
        "title": "...",
        "segments": {
            "一、标题": ["（一）内容...", "（二）内容..."],
            "二、标题": ["（一）内容..."]
        }
    }

    6) 混合结构（章节前有数字标题前言）：
    {
        "title": "...",
        "segments": {
            "一、前言标题": ["（一）内容..."],
            "第一章": ["第一条 ..."]
        }
    }
"""

import os
import re
from typing import Any, Dict, List, Optional, Union

__all__ = ["build_segments_struct", "format_segments_output"]


def _normalize_text(text: str) -> str:
    """
    标准化空白与无效标记，移除页码等噪声，保留换行用于行首锚定。
    合并第一版和第二版的所有清理功能。
    """
    if not text:
        return ""

    # 统一换行
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # === 第一版功能：移除 HTML 注释 ===
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # === 第一版功能：移除 Markdown 图片引用 ===
    # 移除 Markdown 图片引用（支持跨行/含查询参数），如 ![](http://.../a.jpg)
    text = re.sub(
        r"!\[[^\]]*?\]\(\s*https?://[^)]*?\.(?:png|jpe?g|gif|bmp|webp)[^)]*?\)",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # === 第二版功能：改进的页码处理 - 更全面的页码格式匹配 ===
    dash_patterns = [
        # 标准格式：— 1 —, — 16 —
        r"^\s*—+\s*\d+\s*—+\s*$",
        # 变体格式：- 1 -, –16–, ——1——
        r"^\s*[-–—]+\s*\d+\s*[-–—]+\s*$",
        # 中文数字页码：一5一, 一16一, 一1一
        r"^\s*一+\s*\d+\s*一+\s*$",
        # 单侧破折号：— 1, 1 —, 一1, 1一
        r"^\s*[—一]+\s*\d+\s*$",
        r"^\s*\d+\s*[—一]+\s*$",
        # 纯数字页码（独立成行）
        r"^\s*\d{1,3}\s*$",
        # 带括号的页码：（1）, [1]
        r"^\s*[（\(\[]\s*\d+\s*[）\)\]]\s*$",
        # 其他可能的页码格式
        r"^\s*第\s*\d+\s*页\s*$",
        r"^\s*Page\s+\d+\s*$",
    ]

    # 逐个应用页码清理规则
    for pattern in dash_patterns:
        text = re.sub(pattern, "", text, flags=re.MULTILINE | re.IGNORECASE)

    # 处理行中出现的页码（非行首）
    inline_page_patterns = [
        # 行中的破折号页码
        r"—+\s*\d+\s*—+",
        r"[-–]+\s*\d+\s*[-–]+",
        # 行中的中文数字页码
        r"一+\s*\d+\s*一+",
    ]

    for pattern in inline_page_patterns:
        text = re.sub(pattern, " ", text)

    # === 第二版功能：清理其他标记和OCR错误 ===
    # 移除常见的文档标记和乱码
    text = re.sub(r"^\s*【.*?】\s*$", "", text, flags=re.MULTILINE)  # 【备注】等
    text = re.sub(r"^\s*\*{3,}.*?\*{3,}\s*$", "", text, flags=re.MULTILINE)  # ***分隔线***
    text = re.sub(r"^\s*={3,}\s*$", "", text, flags=re.MULTILINE)  # ======分隔线
    text = re.sub(r"^\s*-{3,}\s*$", "", text, flags=re.MULTILINE)  # ------分隔线

    # 清理OCR识别错误和乱码字符
    ocr_noise_patterns = [
        # 文档末尾常见的OCR乱码
        r"[剧黯潍撇粼鹳鐾霭麟]{2,}",  # 连续的复杂汉字（通常是乱码）
        # 单个出现的复杂生僻字（可能是OCR错误）
        r"[鐾霭麟鹳黯潍撇粼](?![a-zA-Z\u4e00-\u9fa5])",
        # 数字字母混杂的乱码
        r"[a-zA-Z]\d{1,2}[a-zA-Z]{1,3}\d*",
        # 特殊符号乱码
        r"[∶∷⋯]{2,}",
        # 连续的特殊标点符号
        r"[，。；：]{3,}",
        # 不规则的空格和特殊字符组合
        r"[\s]*[▪▫■□▲△]{2,}[\s]*",
    ]

    for pattern in ocr_noise_patterns:
        text = re.sub(pattern, "", text)

    # 清理文档页脚/页眉信息
    footer_header_patterns = [
        # 抄送信息行
        r"^\s*抄送[:：].*$",
        # 印发信息行
        r"^\s*.*印发\s*$",
        r"^\s*.*办公厅.*年.*月.*日.*$",
        # 此页无正文
        r"^\s*[\(（]?\s*此页无正文\s*[\)）]?\s*$",
        # 机关名称（独立成行）
        r"^\s*国家发展改革委\s*$",
        r"^\s*国家发展改革委办公厅\s*$",
        # 日期格式
        r"^\s*\d{4}年\d{1,2}月\d{1,2}日\s*$",
    ]

    for pattern in footer_header_patterns:
        text = re.sub(pattern, "", text, flags=re.MULTILINE)

    # 清理重复的标点符号
    text = re.sub(r"([，。；：！？])\1{2,}", r"\1", text)  # 连续3个以上相同标点改为1个

    # 清理孤立的单个字符（可能是OCR错误）
    text = re.sub(r"^\s*[^\u4e00-\u9fa5a-zA-Z0-9]\s*$", "", text, flags=re.MULTILINE)

    # === 第一版功能：OCR标题修复逻辑 ===
    # 预处理：若一级/二级/三级标题与上级标题在同一行，强制在其前插入换行
    # 一级：一、 二、 三、 …（处理 OCR 行内合并导致的一、未换行情况）
    text = re.sub(r"(?<!\n)([一二三四五六七八九十]+、)", r"\n\1", text)
    # 二级：（一）/(一) 可能出现在段首且后面直接跟正文，视为一个标题，需换行锚定
    text = re.sub(r"(?<!\n)([（(][一二三四五六七八九十]+[）)])", r"\n\1", text)
    # 三级：1. / 1、 / 1) 作为子项时也需要换行
    text = re.sub(r"(?<!\n)(\d+[\.、)])", r"\n\1", text)

    # 简单清理
    text = text.replace("*", "")
    text = text.replace("#", "")

    # 行内空白归一并过滤空行
    lines = []
    for ln in text.split("\n"):
        # 标准化行内空白
        cleaned_line = re.sub(r"\s+", " ", ln).strip()
        if cleaned_line:
            lines.append(cleaned_line)

    text = "\n".join(lines)

    # 最后清理：移除过多的连续空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


def _extract_document_title(file_name: Optional[str], file_content: str) -> Optional[str]:
    """优先使用文件名（去扩展名）作为题目；若无，则尝试使用正文首行非空行。"""
    if file_name:
        base_name = os.path.basename(file_name)
        title = "".join(base_name.split(".")[:-1]) or base_name
        return title.strip() or None

    # 回退：正文第一行非空且非各种标题样式
    for line in re.split(r"[\r\n]+", file_content or ""):
        candidate = line.strip()
        if not candidate:
            continue
        # 跳过各种标题格式
        if re.match(r"^(第[一二三四五六七八九十\d]+[章条节]|[一二三四五六七八九十]+、|（[一二三四五六七八九十]+）|\d+\.)",
                    candidate):
            continue
        return candidate
    return None


def build_segments_struct(file_content: str, file_name: Optional[str] = None) -> Dict[str, Any]:
    """
    生成分段结构，合并第一版和第二版的所有功能：
    1. 传统格式：第一章、第一节、第一条
    2. 二级标题格式：一、（一）
    3. 三级标题格式：一、（一）、1.
    4. 混合格式：章节前有数字标题前言
    """
    if not file_content:
        return {"title": ("" if not file_name else _extract_document_title(file_name, "") or ""), "segments": []}

    content = _normalize_text(file_content)
    title = _extract_document_title(file_name, content) or ""

    # === 第二版功能：支持中英文括号的正则表达式 ===
    # 传统格式
    chapter_heading_re = re.compile(r"^\s*第\s*[一二三四五六七八九十百千O0-9０-９]+\s*章[^\n]*", re.M)
    section_heading_re = re.compile(r"^\s*第\s*[一二三四五六七八九十百千O0-9０-９]+\s*节[^\n]*", re.M)
    article_heading_re = re.compile(r"^\s*第\s*[一二三四五六七八九十百千零O0-9０-９]+\s*条[^\n]*", re.M)

    # 三级标题格式
    level1_heading_re = re.compile(r"^\s*[一二三四五六七八九十百千]+、[^\n]*", re.M)  # 一、二、三、
    level2_heading_re = re.compile(r"^\s*[（\(][一二三四五六七八九十百千]+[）\)][^\n]*", re.M)  # 支持（一）和(一)
    level3_heading_re = re.compile(r"^\s*\d+\.[^\n]*", re.M)  # 1. 2. 3.

    # 二级标题格式
    simple_level1_re = re.compile(r"^\s*[一二三四五六七八九十百千]+、[^\n]*", re.M)  # 一、二、三、
    simple_level2_re = re.compile(r"^\s*[（\(][一二三四五六七八九十百千]+[）\)][^\n]*", re.M)  # 支持（一）和(一)

    try:
        # === 第二版功能：结构检测逻辑 ===
        has_chapters = bool(chapter_heading_re.search(content))
        has_level1 = bool(level1_heading_re.search(content))
        has_simple_level1 = bool(simple_level1_re.search(content))
        has_simple_level2 = bool(simple_level2_re.search(content))
        has_level3 = bool(level3_heading_re.search(content))

        print(f"结构检测结果: 章节={has_chapters}, 一级={has_level1}, 二级={has_simple_level2}, 三级={has_level3}")

        if has_chapters:
            # === 第一版功能：混合结构处理 ===
            # 若存在"章"，先提取首章前的前言（按数字多级结构），再解析首章及之后的传统结构
            first_ch = chapter_heading_re.search(content)
            preface_segments: Dict[str, Any] = {}
            remaining_content = content
            if first_ch:
                preface_chunk = content[:first_ch.start()].strip()
                remaining_content = content[first_ch.start():]
                if preface_chunk:
                    preface_struct = _build_three_level_structure(
                        preface_chunk,
                        title,
                        level1_heading_re,
                        level2_heading_re,
                        level3_heading_re,
                    )
                    if isinstance(preface_struct.get("segments"), dict):
                        preface_segments = preface_struct["segments"]

            traditional_struct = _build_traditional_structure(
                remaining_content,
                title,
                chapter_heading_re,
                section_heading_re,
                article_heading_re,
            )
            merged: Dict[str, Any] = {}
            if isinstance(preface_segments, dict):
                merged.update(preface_segments)
            if isinstance(traditional_struct.get("segments"), dict):
                merged.update(traditional_struct["segments"])
            return {"title": title, "segments": merged}

        elif has_simple_level1 and has_simple_level2 and not has_level3:
            # === 第二版功能：二级标题格式 ===
            print("识别为二级标题结构")
            return _build_two_level_structure(content, title, simple_level1_re, simple_level2_re)
        elif has_level1:
            # 三级标题格式处理
            print("识别为三级标题结构")
            return _build_three_level_structure(content, title, level1_heading_re, level2_heading_re,
                                                level3_heading_re)
        else:
            # 无明确结构，尝试按条款处理
            articles = _split_by_heading(content, article_heading_re)
            if articles:
                article_list = []
                for art in articles:
                    text = (art["title"] + " " + art["body"]).strip()
                    if text:
                        article_list.append(text)
                return {"title": title, "segments": article_list}
            else:
                # 尝试按三级标题处理
                level3_items = _split_by_heading(content, level3_heading_re)
                if level3_items:
                    item_list = []
                    for item in level3_items:
                        text = (item["title"] + " " + item["body"]).strip()
                        if text:
                            item_list.append(text)
                    return {"title": title, "segments": item_list}
                else:
                    return {"title": title, "segments": []}

    except Exception as exc:
        print(f"构建层级分段时发生错误: {exc}")
        return {"title": title, "segments": []}


def _build_two_level_structure(content: str, title: str, level1_re: re.Pattern, level2_re: re.Pattern) -> Dict[
    str, Any]:
    """第二版功能：构建二级标题结构：一、（一）"""
    level1_items = _split_by_heading(content, level1_re)
    if not level1_items:
        return {"title": title, "segments": []}

    result_segments: Dict[str, Any] = {}

    for l1_item in level1_items:
        l1_title = l1_item["title"].strip()
        l1_body = l1_item["body"]

        # 检查是否有二级标题
        level2_items = _split_by_heading(l1_body, level2_re)

        if not level2_items:
            # 无二级标题，直接作为内容
            content_text = l1_body.strip()
            if content_text:
                result_segments[l1_title] = [content_text]
            else:
                result_segments[l1_title] = []
        else:
            # 有二级标题 - 保持层级结构
            l2_dict: Dict[str, List[str]] = {}

            # 处理第一个二级标题前的内容
            first_level2_start = level2_items[0]["title"]
            first_level2_pos = l1_body.find(first_level2_start)
            if first_level2_pos > 0:
                pre_level2_content = l1_body[:first_level2_pos].strip()
                if pre_level2_content:
                    l2_dict["前置内容"] = [pre_level2_content]

            # 处理各个二级标题 - 保持结构层次
            for l2_item in level2_items:
                l2_title = l2_item["title"].strip()
                l2_body = l2_item["body"].strip()

                # 保持层级结构，不合并标题和内容
                if l2_body:
                    l2_dict[l2_title] = [l2_body]
                else:
                    l2_dict[l2_title] = []

            result_segments[l1_title] = l2_dict

    return {"title": title, "segments": result_segments}


def _build_traditional_structure(content: str, title: str, chapter_re: re.Pattern, section_re: re.Pattern,
                                 article_re: re.Pattern) -> Dict[str, Any]:
    """构建传统章节结构（增强版：处理混合层级）"""

    # Helper: 按同级标题切块
    def split_by_heading(chunk: str, heading_re: re.Pattern) -> List[Dict[str, Any]]:
        return _split_by_heading(chunk, heading_re)

    # 顶层：章节
    chapters = split_by_heading(content, chapter_re)
    if not chapters:
        # 无章节：直接抽取条款（按行首条款标题切）
        articles = split_by_heading(content, article_re)
        article_list: List[str] = []
        for art in articles:
            text = (art["title"] + " " + art["body"]).strip()
            if text:
                article_list.append(text)
        return {"title": title, "segments": article_list}

    # 有章节：处理混合层级结构
    result_segments: Dict[str, Any] = {}

    # 处理章节前的条款（如果有）
    first_chapter_start = chapters[0]["title"]
    first_chapter_pos = content.find(first_chapter_start)
    if first_chapter_pos > 0:
        pre_chapter_content = content[:first_chapter_pos].strip()
        if pre_chapter_content:
            pre_articles = split_by_heading(pre_chapter_content, article_re)
            if pre_articles:
                article_list = []
                for art in pre_articles:
                    text = (art["title"] + " " + art["body"]).strip()
                    if text:
                        article_list.append(text)
                result_segments["前置条款"] = article_list

    # 处理每个章节
    for ch in chapters:
        ch_title = ch["title"].strip()
        ch_body = ch["body"]

        # 检查章节内是否有节
        sections = split_by_heading(ch_body, section_re)

        if not sections:
            # 无节：直接处理章节内的条款
            articles = split_by_heading(ch_body, article_re)
            article_list = []
            for a in articles:
                text = (a["title"] + " " + a["body"]).strip()
                if text:
                    article_list.append(text)
            result_segments[ch_title] = article_list
        else:
            # 有节：需要处理节前的条款 + 各节内的条款
            sect_map: Dict[str, List[str]] = {}

            # 处理第一节前的条款
            first_section_start = sections[0]["title"]
            first_section_pos = ch_body.find(first_section_start)
            if first_section_pos > 0:
                pre_section_content = ch_body[:first_section_pos].strip()
                if pre_section_content:
                    pre_articles = split_by_heading(pre_section_content, article_re)
                    if pre_articles:
                        article_list = []
                        for art in pre_articles:
                            text = (art["title"] + " " + art["body"]).strip()
                            if text:
                                article_list.append(text)
                        sect_map["章节前置条款"] = article_list

            # 处理各节
            for sec in sections:
                sec_title = sec["title"].strip()
                sec_body = sec["body"]
                articles = split_by_heading(sec_body, article_re)
                article_list = []
                for a in articles:
                    text = (a["title"] + " " + a["body"]).strip()
                    if text:
                        article_list.append(text)
                sect_map[sec_title] = article_list

            result_segments[ch_title] = sect_map

    return {"title": title, "segments": result_segments}


def _build_three_level_structure(content: str, title: str, level1_re: re.Pattern, level2_re: re.Pattern,
                                 level3_re: re.Pattern) -> Dict[str, Any]:
    """第一版功能：构建三级标题结构：一、（一）、1. - 简洁版本"""
    level1_items = _split_by_heading(content, level1_re)
    if not level1_items:
        return {"title": title, "segments": []}

    result_segments: Dict[str, Any] = {}

    for l1 in level1_items:
        l1_title = l1["title"].strip()
        l1_body = l1["body"]

        level2_items = _split_by_heading(l1_body, level2_re)
        if not level2_items:
            # 无二级：整体作为一个分块（不再按第三级拆分）
            content_text = l1_body.strip()
            result_segments[l1_title] = ([content_text] if content_text else [])
        else:
            l2_map: Dict[str, List[str]] = {}
            # 处理第一个二级标题之前的第三级项目（或正文）
            l2_matches = list(level2_re.finditer(l1_body))
            if l2_matches:
                before_first_l2 = l1_body[:l2_matches[0].start()].strip()
                if before_first_l2:
                    l2_map[""] = [before_first_l2]

            for l2 in level2_items:
                l2_title = l2["title"].strip()
                l2_body = l2["body"]
                # 每个二级标题的正文整体作为一个分块（不再按第三级拆分）
                content_text = l2_body.strip()
                l2_map[l2_title] = ([content_text] if content_text else [])

            result_segments[l1_title] = l2_map

    return {"title": title, "segments": result_segments}


def _split_by_heading(chunk: str, heading_re: re.Pattern) -> List[Dict[str, Any]]:
    """按同级标题切块的辅助函数"""
    items: List[Dict[str, Any]] = []
    matches = list(heading_re.finditer(chunk))
    if not matches:
        return items

    for idx, m in enumerate(matches):
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(chunk)
        title_line = m.group().strip()
        body = chunk[m.end():end].strip()
        items.append({"title": title_line, "body": body})

    return items


def format_segments_output(segments: Union[List, dict, str], path: str = "", file_name: Optional[str] = None) -> List[
    str]:
    """
    递归提取层级结构中的"条款文本"列表，带章节路径。
    兼容第一版（带文件名）和第二版（不带文件名）的调用方式。

    参数：
    - segments: 要格式化的段落结构
    - path: 当前路径（用于递归）
    - file_name: 可选的文件名，如果提供会添加到输出前缀

    返回示例：
    有文件名: ["文件名 第一章 第一节 第一条 ...", "文件名 第一章 第一节 第二条 ..."]
    无文件名: ["第一章 第一节 第一条 ...", "第一章 第一节 第二条 ..."]
    或
    ["一、绿色电力交易的定义 （一）内容...", "一、绿色电力交易的定义 （二）内容..."]
    """
    results: List[str] = []

    try:
        if isinstance(segments, str):  # 最底层：条款
            text = segments.strip()
            if text:
                if file_name:
                    results.append(f"{file_name} {path.strip()} {text}".strip())  # 拼接文件名和路径
                else:
                    results.append(f"{path.strip()} {text}".strip())  # 只拼接路径

        elif isinstance(segments, list):  # 列表：逐个递归
            for s in segments:
                results.extend(format_segments_output(s, path, file_name))

        elif isinstance(segments, dict):  # 字典
            if "segments" in segments:
                results.extend(format_segments_output(segments["segments"], path, file_name))
            else:
                for key, value in segments.items():
                    new_path = f"{path} {key}".strip()  # 路径叠加
                    results.extend(format_segments_output(value, new_path, file_name))

    except Exception as exc:
        print(f"格式化输出时发生错误: {exc}")

    return results