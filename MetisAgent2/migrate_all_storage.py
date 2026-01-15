#!/usr/bin/env python3
"""
Storage Migration Script - ChromaDB ve JSON'dan SQLite'a geçiş
"""

import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from tools.migration_helper import get_migration_helper

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Ana migration script"""
    print("🚀 MetisAgent2 Storage Migration")
    print("=" * 50)
    
    try:
        migration_helper = get_migration_helper()
        
        # 1. Backup oluştur
        print("\n📦 Creating backup...")
        backup_dir = migration_helper.create_migration_backup()
        print(f"✅ Backup created: {backup_dir}")
        
        # 2. Migration başlat
        print("\n🔄 Starting migration...")
        migration_results = migration_helper.migrate_all_to_sqlite()
        
        # 3. Sonuçları yazdır
        print("\n📊 Migration Results:")
        print("-" * 30)
        
        # ChromaDB sonuçları
        chroma_results = migration_results['chromadb_migration']
        print(f"👥 Users migrated from ChromaDB: {chroma_results['users_migrated']}")
        print(f"🔑 API Keys migrated: {chroma_results['api_keys_migrated']}")
        print(f"🎭 Personas migrated: {chroma_results['personas_migrated']}")
        
        # JSON sonuçları
        json_results = migration_results['json_migration']
        print(f"🔐 OAuth tokens migrated: {json_results['oauth_tokens_migrated']}")
        print(f"📝 User settings migrated: {json_results['user_settings_migrated']}")
        print(f"🧠 Graph memory migrated: {json_results['graph_memory_migrated']}")
        
        # Hata sayısı
        total_errors = migration_results['total_errors']
        print(f"\n❌ Total errors: {total_errors}")
        
        if total_errors > 0:
            print("\n🔍 Error details:")
            for error in chroma_results.get('errors', []):
                print(f"  - ChromaDB: {error}")
            for error in json_results.get('errors', []):
                print(f"  - JSON: {error}")
        
        # 4. Validation
        print("\n🔍 Validating migration...")
        validation_results = migration_helper.validate_migration()
        
        print(f"✅ SQLite users count: {validation_results['sqlite_users_count']}")
        print(f"✅ SQLite properties count: {validation_results['sqlite_properties_count']}")
        
        if validation_results.get('sample_user_data'):
            sample = validation_results['sample_user_data']
            print(f"📋 Sample user: {sample['user_id']} ({sample['properties_count']} properties)")
        
        # 5. Migration sonuç raporu kaydet
        report_file = f"migration_report_{migration_results['migration_timestamp'].replace(':', '-').replace('.', '_')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'migration_results': migration_results,
                'validation_results': validation_results,
                'backup_directory': backup_dir
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📋 Migration report saved: {report_file}")
        
        # 6. Son durum
        if validation_results['validation_passed'] and total_errors == 0:
            print("\n🎉 Migration completed successfully!")
            print("✅ All data migrated to SQLite")
            print("✅ Validation passed")
        else:
            print("\n⚠️  Migration completed with issues:")
            if not validation_results['validation_passed']:
                print("❌ Validation failed")
            if total_errors > 0:
                print(f"❌ {total_errors} errors occurred")
        
        print(f"\n📁 Backup saved at: {backup_dir}")
        print(f"📄 Migration log: migration.log")
        print(f"📊 Full report: {report_file}")
        
    except Exception as e:
        logger.error(f"Migration script error: {e}")
        print(f"\n💥 Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()