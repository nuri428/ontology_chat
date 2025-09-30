// Company 노드 인덱스
CREATE INDEX company_name_idx IF NOT EXISTS FOR (c:Company) ON (c.name);
CREATE TEXT INDEX company_name_text_idx IF NOT EXISTS FOR (c:Company) ON (c.name);

// Event 노드 인덱스
CREATE TEXT INDEX event_title_text_idx IF NOT EXISTS FOR (e:Event) ON (e.title);

// Technology 노드 인덱스  
CREATE TEXT INDEX tech_name_text_idx IF NOT EXISTS FOR (t:Technology) ON (t.name);

// Theme 노드 인덱스
CREATE TEXT INDEX theme_name_text_idx IF NOT EXISTS FOR (t:Theme) ON (t.name);

// News 노드 인덱스
CREATE TEXT INDEX news_title_text_idx IF NOT EXISTS FOR (n:News) ON (n.title);

// 복합 인덱스 (시간 필터링용)
CREATE INDEX event_date_idx IF NOT EXISTS FOR (e:Event) ON (e.date);
CREATE INDEX news_date_idx IF NOT EXISTS FOR (n:News) ON (n.published_date);
