# 数据库表清理工具

## 功能说明

`clean_tables.py` 是一个用于清空 SQLite 数据库中 collections、documents、chunks 三个数据表内容的工具。

## 使用方法

### 1. 查看表记录数量

```bash
python temp_tools/clean_tables.py --show
```

### 2. 清空所有表（默认）

```bash
# 交互式确认
python temp_tools/clean_tables.py

# 跳过确认，直接执行
python temp_tools/clean_tables.py --confirm
```

### 3. 清空指定表

```bash
# 清空 chunks 表
python temp_tools/clean_tables.py --table chunks

# 清空 documents 表
python temp_tools/clean_tables.py --table documents

# 清空 collections 表
python temp_tools/clean_tables.py --table collections
```

### 4. 查看帮助信息

```bash
python temp_tools/clean_tables.py --help
```

## 参数说明

- `--table`: 指定要清空的表名
  - `collections`: 清空集合表
  - `documents`: 清空文档表
  - `chunks`: 清空分块表
  - `all`: 清空所有表（默认值）

- `--show`: 仅显示各表的记录数量，不执行清空操作

- `--confirm`: 跳过确认提示，直接执行清空操作

## 注意事项

1. **数据不可恢复**：清空操作会永久删除数据，请谨慎使用
2. **外键约束**：工具会按正确的顺序清空表（先 chunks，再 documents，最后 collections）
3. **自动初始化**：如果数据库文件不存在，工具会自动创建并初始化表结构
4. **事务安全**：所有操作都在事务中执行，出错时会自动回滚

## 示例输出

```
$ python temp_tools/clean_tables.py --show
当前数据表记录数量：
------------------------------
collections :      5 条记录
documents   :     10 条记录
chunks      :    148 条记录

$ python temp_tools/clean_tables.py --table chunks --confirm
清空操作前的数据表状态：
当前数据表记录数量：
------------------------------
collections :      5 条记录
documents   :     10 条记录
chunks      :    148 条记录

开始清空 chunks 表...
✓ 已清空 chunks 表，删除了 148 条记录

清空操作后的数据表状态：
当前数据表记录数量：
------------------------------
collections :      5 条记录
documents   :     10 条记录
chunks      :      0 条记录
```