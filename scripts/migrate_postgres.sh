#!/bin/bash

 python -m scripts.migrate migrations/000_drop_database.sql
 python -m scripts.migrate migrations/roles/
 python -m scripts.migrate migrations/001_create_extensions.sql
 python -m scripts.migrate migrations/002_create_core_functions.sql
 python -m scripts.migrate migrations/003_create_tables.sql
 python -m scripts.migrate migrations/004_create_search_functions.sql
 python -m scripts.migrate migrations/006_usage_examples.sql
 python -m scripts.migrate migrations/007_security_policies.sql
 python -m scripts.migrate migrations/008_fix_ai_results_id.sql
 python -m scripts.migrate migrations/009_saas_multitenant.sql
 python -m scripts.migrate migrations/010_register_organization_rpc.sql
 python -m scripts.migrate migrations/011_fix_ai_results_feature_fk.sql
 python -m scripts.migrate migrations/012_recreate_ai_results.sql
 python -m scripts.migrate migrations/feature/
 