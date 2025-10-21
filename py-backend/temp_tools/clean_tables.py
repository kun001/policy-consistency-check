"""清空数据库的内容"""

import sys
import os
import sqlite3
from pathlib import Path


def get_db_connection():
    """获取数据库连接"""
    # 数据库文件路径 - 根据 src/storage/db.py 的配置
    backend_root = Path(__file__).parent.parent
    storage_root = backend_root / "storage"
    db_path = storage_root / "db.sqlite3"
    
    if not db_path.exists():
        # 尝试初始化数据库
        print(f"数据库文件不存在，尝试初始化：{db_path}")
        storage_root.mkdir(parents=True, exist_ok=True)
        (storage_root / "docs").mkdir(parents=True, exist_ok=True)
        (storage_root / "tmp").mkdir(parents=True, exist_ok=True)
        
        # 创建空的数据库文件并初始化表结构
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        initialize_schema(conn)
        conn.close()
        print(f"✓ 数据库已初始化：{db_path}")
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    """创建数据库表结构（与 src/storage/db.py 保持一致）"""
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA foreign_keys = ON;

        -- collections 表
        CREATE TABLE IF NOT EXISTS collections (
          id TEXT PRIMARY KEY,
          name TEXT,
          description TEXT,
          provider TEXT,
          config TEXT,
          is_active INTEGER DEFAULT 1,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- documents 表
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY,
          collection_id TEXT,
          source_filename TEXT,
          storage_path TEXT,
          original_mime TEXT,
          status TEXT,
          page_count INTEGER,
          word_count INTEGER,
          summary TEXT,
          keywords TEXT,
          parsing_payload TEXT,
          last_error TEXT,
          version INTEGER DEFAULT 1,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection_id);

        -- chunks 表
        CREATE TABLE IF NOT EXISTS chunks (
          id TEXT PRIMARY KEY,
          doc_id TEXT,
          collection_id TEXT,
          chunk_index INTEGER,
          title TEXT,
          section_path TEXT,
          content TEXT,
          token_count INTEGER,
          metadata TEXT,
          weaviate_id TEXT,
          embedding_status TEXT,
          last_error TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_weaviate ON chunks(weaviate_id);
        """
    )
    conn.commit()


def clean_all_tables():
    """清空 collections、documents、chunks 三个数据表的所有内容"""
    try:
        # 建立数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("开始清空数据表...")
        
        # 清空 chunks 表（需要先清空，因为有外键依赖）
        cursor.execute("DELETE FROM chunks")
        chunks_deleted = cursor.rowcount
        print(f"✓ 已清空 chunks 表，删除了 {chunks_deleted} 条记录")
        
        # 清空 documents 表
        cursor.execute("DELETE FROM documents")
        documents_deleted = cursor.rowcount
        print(f"✓ 已清空 documents 表，删除了 {documents_deleted} 条记录")
        
        # 清空 collections 表
        cursor.execute("DELETE FROM collections")
        collections_deleted = cursor.rowcount
        print(f"✓ 已清空 collections 表，删除了 {collections_deleted} 条记录")
        
        # 提交事务
        conn.commit()
        
        print(f"\n🎉 数据表清空完成！")
        print(f"总计删除记录数：{chunks_deleted + documents_deleted + collections_deleted}")
        
        # 关闭连接
        conn.close()
        
    except Exception as e:
        print(f"❌ 清空数据表时发生错误：{e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise


def clean_specific_table(table_name: str):
    """清空指定的数据表
    
    Args:
        table_name: 表名，可选值：'collections', 'documents', 'chunks'
    """
    valid_tables = ['collections', 'documents', 'chunks']
    if table_name not in valid_tables:
        print(f"❌ 无效的表名：{table_name}")
        print(f"有效的表名：{', '.join(valid_tables)}")
        return
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print(f"开始清空 {table_name} 表...")
        
        cursor.execute(f"DELETE FROM {table_name}")
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✓ 已清空 {table_name} 表，删除了 {deleted_count} 条记录")
        
    except Exception as e:
        print(f"❌ 清空 {table_name} 表时发生错误：{e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise


def show_table_counts():
    """显示各个表的记录数量"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        tables = ['collections', 'documents', 'chunks']
        print("当前数据表记录数量：")
        print("-" * 30)
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table:12}: {count:>6} 条记录")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 查询表记录数时发生错误：{e}")
        if 'conn' in locals():
            conn.close()
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库表清理工具")
    parser.add_argument(
        "--table", 
        choices=['collections', 'documents', 'chunks', 'all'],
        default='all',
        help="要清空的表名，默认清空所有表"
    )
    parser.add_argument(
        "--show", 
        action="store_true",
        help="显示各表的记录数量"
    )
    parser.add_argument(
        "--confirm", 
        action="store_true",
        help="跳过确认提示，直接执行清空操作"
    )
    
    args = parser.parse_args()
    
    try:
        if args.show:
            show_table_counts()
        else:
            # 显示当前状态
            print("清空操作前的数据表状态：")
            show_table_counts()
            print()
            
            # 确认操作
            if not args.confirm:
                if args.table == 'all':
                    confirm = input("⚠️  确定要清空所有数据表吗？此操作不可恢复！(y/N): ")
                else:
                    confirm = input(f"⚠️  确定要清空 {args.table} 表吗？此操作不可恢复！(y/N): ")
                
                if confirm.lower() not in ['y', 'yes']:
                    print("操作已取消")
                    sys.exit(0)
            
            # 执行清空操作
            if args.table == 'all':
                clean_all_tables()
            else:
                clean_specific_table(args.table)
            
            print()
            print("清空操作后的数据表状态：")
            show_table_counts()
            
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n程序执行出错：{e}")
        sys.exit(1)