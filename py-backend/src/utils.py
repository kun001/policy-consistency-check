import os
import re
import csv
from datetime import datetime
from typing import List, Optional, Union

def save_segments2csv(format_segments, file_name=None, output_dir="output"):
    """
    保存为CSV格式，方便知识库的批量导入
    
    Args:
        format_segments (list): 条款列表
    """
    try:
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 生成文件名
        if file_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"policy_segments_{timestamp}.csv"
        
        # 确保文件名以.csv结尾
        if not file_name.endswith('.csv'):
            file_name += '.csv'
        
        file_path = os.path.join(output_dir, file_name)
        
        # 写入CSV文件
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # 写入表头
            writer.writerow(['分段内容'])
            
            # 写入每个分段
            for segment in format_segments:
                # 清理分段内容，去除多余的换行和空格
                clean_segment = re.sub(r'\s+', ' ', segment).strip()
                if clean_segment:
                    writer.writerow([clean_segment])
        
        print(f"CSV文件已保存到: {file_path}")
        print(f"共保存了 {len(format_segments)} 个分段")
        
        return file_path
        
    except Exception as e:
        print(f"保存CSV文件时发生错误: {e}")
        return None


# 构建层级 TOC 结构（章-节-条）
def build_toc(segments: Union[List, dict]) -> tuple[dict, dict]:
    counts = {"chapters": 0, "sections": 0, "articles": 0}
    doc_children: List[dict] = []

    def parse_article(line: str) -> dict:
        text_line = (line or "").strip()
        m = re.match(r"^\s*(第[一二三四五六七八九十百千零O0-9０-９]+条)\s*(.*)$", text_line)
        label = None
        body = text_line
        if m:
            label = m.group(1).strip()
            body = (m.group(2) or "").strip()
        counts["articles"] += 1
        return {
            "id": f"art-{counts['articles']}",
            "type": "article",
            "label": label,
            "index": counts["articles"],
            "text": (f"{label} {body}".strip() if label else body)
        }

    def build_chapter(label: str, value: Union[List, dict]) -> dict:
        counts["chapters"] += 1
        ch_idx = counts["chapters"]
        children: List[dict] = []

        if isinstance(value, list):
            for a in value:
                children.append(parse_article(a))
        elif isinstance(value, dict):
            # 章节前置条款（如果存在）
            if "章节前置条款" in value and isinstance(value["章节前置条款"], list):
                for a in value["章节前置条款"]:
                    children.append(parse_article(a))
            # 处理各节
            for sec_label, sec_value in value.items():
                if sec_label == "章节前置条款":
                    continue
                counts["sections"] += 1
                sec_idx = counts["sections"]
                sec_children: List[dict] = []
                if isinstance(sec_value, list):
                    for a in sec_value:
                        sec_children.append(parse_article(a))
                elif isinstance(sec_value, dict):
                    # 非预期的更深层结构，尽量扁平化为条款
                    for maybe_list in sec_value.values():
                        if isinstance(maybe_list, list):
                            for a in maybe_list:
                                sec_children.append(parse_article(a))
                children.append({
                    "id": f"sec-{sec_idx}",
                    "type": "section",
                    "label": sec_label,
                    "index": sec_idx,
                    "children": sec_children
                })

        return {
            "id": f"ch-{ch_idx}",
            "type": "chapter",
            "label": label,
            "index": ch_idx,
            "children": children
        }

    if isinstance(segments, list):
        for a in segments:
            doc_children.append(parse_article(a))
    elif isinstance(segments, dict):
        # 前置条款（直接挂在文档下）
        if "前置条款" in segments and isinstance(segments["前置条款"], list):
            for a in segments["前置条款"]:
                doc_children.append(parse_article(a))
        for top_label, value in segments.items():
            if top_label == "前置条款":
                continue
            # 仅优先识别“第..章”为章节；否则尽力构造为章节
            if "章" in top_label or isinstance(value, dict):
                doc_children.append(build_chapter(top_label, value))
            else:
                # 非章节键但值为列表，作为文档下的条款
                if isinstance(value, list):
                    for a in value:
                        doc_children.append(parse_article(a))

    toc = {"id": "doc-1", "type": "document", "children": doc_children}
    return toc, counts