-- supabase/migrations/20260427_kol_project_tracking.sql
create table if not exists kol_project_tracking (
    id bigserial primary key,
    project_name text not null,
    kol_name text not null,
    mention_date date not null,
    context text not null default '',
    sentiment text not null default '中性' constraint chk_sentiment check (sentiment in ('看多', '看空', '中性')),
    research_status text not null default '待研究' constraint chk_research_status check (research_status in ('待研究', '研究中', '已完成', '不感兴趣')),
    created_at timestamptz not null default now(),
    unique (project_name, kol_name, mention_date)
);

create index if not exists idx_kol_project_name
    on kol_project_tracking (project_name);

create index if not exists idx_kol_mention_date
    on kol_project_tracking (mention_date desc);
