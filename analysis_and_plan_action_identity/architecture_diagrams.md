# Arquitetura SaaS Multi-Tenant - Diagramas

## 1. Modelo de Dados Completo

```mermaid
erDiagram
    %% ========================================
    %% TEMPLATE LAYER (Global System)
    %% ========================================
    
    FEATURES_CATALOG {
        text feature_id PK
        text feature_key UK "immutable"
        text name
        text description
        text feature_type "boolean|quota|tier|config"
        text unit "messages, users, GB"
        text category "integration, ai, analytics"
        integer display_order
        boolean is_public
        boolean is_deprecated
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }
    
    PLANS {
        text plan_id PK
        text name UK
        text display_name
        text description
        integer price_cents
        text billing_period "monthly|yearly|lifetime"
        boolean is_public
        integer max_users
        integer max_projects
        jsonb config_json
        boolean active
        timestamp created_at
        timestamp updated_at
    }
    
    PLAN_VERSIONS {
        text version_id PK
        text plan_id FK
        integer version_number
        integer price_cents "snapshot"
        text billing_period "snapshot"
        integer max_users "snapshot"
        integer max_projects "snapshot"
        timestamp effective_from
        timestamp effective_until
        boolean is_active
        text change_reason
        text changed_by
        text change_type
        jsonb metadata
        timestamp created_at
    }
    
    PLAN_FEATURES {
        bigserial plan_feature_id PK
        text plan_id FK
        text feature_id FK
        boolean is_enabled
        integer quota_limit "NULL=unlimited"
        jsonb config_value
        integer display_order
        boolean is_highlighted
        text description
        timestamp created_at
        timestamp updated_at
    }
    
    %% ========================================
    %% TENANT LAYER (Per Organization)
    %% ========================================
    
    OWNERS {
        text owner_id PK "tenant"
        text name
        text email UK
        boolean active
        timestamp created_at
    }
    
    USERS {
        text user_id PK
        text owner_id FK
        text profile_name
        text first_name
        text last_name
        text role "admin|agent|user"
        text phone
        boolean active
        text auth_id UK
        jsonb preferences
        timestamp created_at
    }
    
    SUBSCRIPTIONS {
        text subscription_id PK
        text owner_id FK
        text plan_id FK
        text plan_version_id FK
        text status "active|trialing|canceled..."
        timestamp current_period_start
        timestamp current_period_end
        timestamp cancel_at
        timestamp canceled_at
        text cancellation_reason
        timestamp trial_start
        timestamp trial_end
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }
    
    FEATURE_USAGE {
        text usage_id PK
        text owner_id FK
        text feature_id FK
        integer current_usage "real-time counter"
        integer quota_limit "inherited or override"
        timestamp period_start
        timestamp period_end
        timestamp last_reset_at
        timestamp last_used_at
        boolean is_override "admin override"
        text override_reason
        text override_by
        timestamp override_at
        boolean is_active
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }
    
    SUBSCRIPTION_EVENTS {
        text event_id PK
        text subscription_id FK
        text event_type "created|upgraded|canceled..."
        text from_plan_id FK
        text to_plan_id FK
        text from_status
        text to_status
        text triggered_by
        text ip_address
        text user_agent
        text reason
        text description
        jsonb metadata
        timestamp created_at
    }
    
    %% ========================================
    %% RELATIONSHIPS
    %% ========================================
    
    %% Template Layer
    PLANS ||--o{ PLAN_VERSIONS : "has versions"
    PLANS ||--o{ PLAN_FEATURES : "includes"
    FEATURES_CATALOG ||--o{ PLAN_FEATURES : "referenced by"
    
    %% Tenant Layer
    OWNERS ||--o{ USERS : "has"
    OWNERS ||--o{ SUBSCRIPTIONS : "subscribes"
    OWNERS ||--o{ FEATURE_USAGE : "tracks"
    
    %% Cross-layer
    PLANS ||--o{ SUBSCRIPTIONS : "subscribed to"
    PLAN_VERSIONS ||--o{ SUBSCRIPTIONS : "locked to version"
    FEATURES_CATALOG ||--o{ FEATURE_USAGE : "instance of"
    
    %% Audit
    SUBSCRIPTIONS ||--o{ SUBSCRIPTION_EVENTS : "logged"
    PLANS ||--o{ SUBSCRIPTION_EVENTS : "from/to plan"
```

## 2. Fluxo de Feature Inheritance

```mermaid
flowchart TD
    Start([Tenant Subscribes to Plan]) --> GetPlan[Get Plan Details]
    GetPlan --> GetPlanFeatures[Load Plan Features]
    
    GetPlanFeatures --> CreateSub[Create Subscription Record]
    CreateSub --> LinkVersion[Link to Current Plan Version]
    
    LinkVersion --> InitUsage{Initialize Feature Usage}
    
    InitUsage -->|For Each Feature| CreateUsage[Create feature_usage Record]
    CreateUsage --> SetQuota[Set quota_limit from Plan]
    SetQuota --> SetPeriod[Set period based on billing]
    SetPeriod --> NextFeature{More Features?}
    
    NextFeature -->|Yes| CreateUsage
    NextFeature -->|No| LogEvent[Log 'created' Event]
    
    LogEvent --> Complete([✓ Tenant Can Use Features])
    
    style Start fill:#e1f5e1
    style Complete fill:#e1f5e1
    style InitUsage fill:#fff4e1
    style CreateUsage fill:#e1f0ff
```

## 3. Fluxo de Verificação de Feature Access

```mermaid
sequenceDiagram
    participant App as Application
    participant FS as FeatureUsageService
    participant DB as Database
    participant Cache as Cache (Optional)
    
    App->>FS: check_feature_access(owner_id, feature_key)
    
    FS->>Cache: Get cached result?
    alt Cache Hit
        Cache-->>FS: Return cached access check
    else Cache Miss
        FS->>DB: SELECT from feature_usage
        DB-->>FS: Return usage record
        
        alt Feature Not Found
            FS-->>App: {allowed: false, reason: "Not enabled"}
        else Feature Found
            FS->>FS: Check if active
            FS->>FS: Check quota (current vs limit)
            
            alt Quota OK
                FS->>Cache: Cache result (TTL: 60s)
                FS-->>App: {allowed: true, usage: X, limit: Y}
            else Quota Exceeded
                FS->>Cache: Cache result (TTL: 60s)
                FS-->>App: {allowed: false, reason: "Quota exceeded"}
            end
        end
    end
    
    alt Feature Allowed
        App->>FS: increment_usage(owner_id, feature_key)
        FS->>DB: UPDATE feature_usage SET current_usage = current_usage + 1
        DB-->>FS: Success
        FS->>Cache: Invalidate cache
        FS-->>App: {success: true, new_usage: X+1}
    end
```

## 4. Fluxo de Upgrade/Downgrade

```mermaid
stateDiagram-v2
    [*] --> Active: Initial Subscription
    
    Active --> UpgradeRequested: User requests upgrade
    UpgradeRequested --> CalculateProration: Calculate prorated amount
    CalculateProration --> ProcessPayment: Charge difference
    
    ProcessPayment --> UpdateSubscription: Payment success
    ProcessPayment --> PaymentFailed: Payment failed
    
    PaymentFailed --> Active: Retry / Keep current plan
    
    UpdateSubscription --> UpdateFeatures: Change plan_id
    UpdateFeatures --> IncreaseQuotas: Increase feature quotas
    IncreaseQuotas --> LogUpgrade: Log 'upgraded' event
    LogUpgrade --> Active: ✓ Upgraded
    
    Active --> DowngradeRequested: User requests downgrade
    DowngradeRequested --> ScheduleDowngrade: Schedule for period end
    ScheduleDowngrade --> PendingDowngrade: Set cancel_at
    
    PendingDowngrade --> PeriodEnd: Wait for current_period_end
    PeriodEnd --> ApplyDowngrade: Apply new plan
    ApplyDowngrade --> DecreaseQuotas: Decrease feature quotas
    DecreaseQuotas --> CheckOverage: Check if over new limits
    
    CheckOverage --> NotifyOverage: Notify if exceeded
    NotifyOverage --> LogDowngrade: Log 'downgraded' event
    LogDowngrade --> Active: ✓ Downgraded
    
    Active --> CancelRequested: User cancels
    CancelRequested --> ImmediateCancel: Immediate?
    ImmediateCancel --> Canceled: Yes - Cancel now
    ImmediateCancel --> ScheduledCancel: No - Cancel at period end
    ScheduledCancel --> PendingCancellation
    
    PendingCancellation --> PeriodEnd2[Period End]
    PeriodEnd2 --> Canceled
    
    Canceled --> [*]
    
    note right of UpdateFeatures
        Updates:
        - subscription.plan_id
        - subscription.plan_version_id
        - feature_usage.quota_limit (for all features)
    end note
    
    note right of CheckOverage
        If current_usage > new quota_limit:
        - Send warning email
        - Optionally disable feature
        - Log override event
    end note
```

## 5. Arquitetura de Módulos (Separação Proposta)

```mermaid
graph TB
    subgraph "src/modules/identity"
        A1[OwnerService]
        A2[UserService]
        A3[AuthService]
        A4[Owner Model]
        A5[User Model]
    end
    
    subgraph "src/modules/billing"
        B1[PlanService]
        B2[SubscriptionService]
        B3[FeatureUsageService]
        B4[FeaturesCatalogService]
        B5[Plan Model]
        B6[Subscription Model]
        B7[FeatureUsage Model]
        B8[Feature Model]
    end
    
    subgraph "src/modules/integrations/payment"
        C1[StripeService]
        C2[PaddleService]
        C3[PaymentGatewayInterface]
    end
    
    subgraph "src/core"
        D1[EventBus]
        D2[Logger]
        D3[Cache]
    end
    
    A1 --> B2
    B2 --> B1
    B2 --> B3
    B2 --> C3
    B3 --> B4
    B1 --> B4
    
    B2 --> D1
    B3 --> D3
    
    C1 -.implements.-> C3
    C2 -.implements.-> C3
    
    style A1 fill:#e1f5e1
    style A2 fill:#e1f5e1
    style B1 fill:#e1f0ff
    style B2 fill:#e1f0ff
    style B3 fill:#fff4e1
    style B4 fill:#fff4e1
```

## 6. Event Flow (Subscription Lifecycle)

```mermaid
timeline
    title Subscription Lifecycle Events
    
    section Creation
        created : Subscription created
        activated : Payment confirmed
        trial_started : Trial period begins
    
    section Active Use
        payment_succeeded : Monthly renewal
        feature_override : Admin increases quota
        payment_failed : Payment declined
        payment_retried : Retry payment
    
    section Plan Changes
        upgraded : Moved to higher plan
        downgraded : Moved to lower plan
        plan_changed : Different plan same tier
    
    section Cancellation
        cancellation_requested : User requests cancel
        cancellation_scheduled : Set to cancel at period end
        canceled : Actually canceled
        cancellation_reverted : User changed mind
    
    section End States
        expired : Trial/subscription ended
        suspended : Admin action
        unpaid : Payment failed permanently
```

## 7. Quota Tracking Flow

```mermaid
graph LR
    A[User Action] --> B{Check Access}
    B -->|Allowed| C[Execute Action]
    B -->|Denied| D[Return Error]
    
    C --> E[Increment Counter]
    E --> F{Approaching Limit?}
    
    F -->|No| G[Continue]
    F -->|Yes 80%| H[Send Warning]
    F -->|Yes 95%| I[Send Critical Warning]
    F -->|Yes 100%| J[Block Further Use]
    
    H --> G
    I --> G
    
    G --> K[Success Response]
    D --> L[Error Response]
    J --> L
    
    style B fill:#fff4e1
    style F fill:#fff4e1
    style J fill:#ffe1e1
```

## 8. Data Migration Strategy

```mermaid
graph TD
    Start([Start Migration]) --> Backup[Backup Current Database]
    Backup --> CreateNew[Create New Tables]
    CreateNew --> MigrateFeatures[Migrate features → features_catalog]
    
    MigrateFeatures --> UpdatePlanFeatures[Update plan_features with FKs]
    UpdatePlanFeatures --> InitVersions[Create initial plan_versions]
    
    InitVersions --> InitUsage{For Each Active Subscription}
    InitUsage --> LoadPlan[Load Plan Features]
    LoadPlan --> CreateUsage[Create feature_usage records]
    CreateUsage --> NextSub{More Subscriptions?}
    
    NextSub -->|Yes| InitUsage
    NextSub -->|No| EnableDualWrite[Enable Dual-Write Mode]
    
    EnableDualWrite --> TestPeriod[Test Period - 7 days]
    TestPeriod --> Validate[Validate Data Consistency]
    
    Validate --> Consistent{Data Consistent?}
    Consistent -->|No| Fix[Fix Issues] --> Validate
    Consistent -->|Yes| SwitchReads[Switch Reads to New Tables]
    
    SwitchReads --> Monitor[Monitor Performance]
    Monitor --> Stable{System Stable?}
    
    Stable -->|No| Rollback[Rollback to Old System]
    Stable -->|Yes| RemoveDual[Remove Dual-Write]
    
    RemoveDual --> DropOld[Drop Old Tables]
    DropOld --> Complete([✓ Migration Complete])
    
    Rollback --> Fix2[Fix Issues] --> EnableDualWrite
    
    style Start fill:#e1f5e1
    style Complete fill:#e1f5e1
    style Rollback fill:#ffe1e1
    style Consistent fill:#fff4e1
    style Stable fill:#fff4e1
```
