    def compute_graph_metrics(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        새로운 상장사 중심 스키마에 맞춘 그래프 메트릭 계산
        - 라벨 분포
        - 계약(Contract) 합계/상위 샘플
        - 재무지표(FinancialMetric) 분석
        - 투자(Investment) 정보
        - 상장사(Company) 중심 분석
        """
        label_counter = Counter()
        contracts: List[Dict[str, Any]] = []
        companies: List[Dict[str, Any]] = []  # 상장사 정보 확장
        programs: List[str] = []
        # weapons 변수는 호환성을 위해 유지하되 products로 대체
        weapons: List[str] = []  # deprecated - use products
        products: List[str] = []  # 새로 추가
        events_sample: List[Dict[str, Any]] = []
        financial_metrics: List[Dict[str, Any]] = []  # 새로 추가
        investments: List[Dict[str, Any]] = []  # 새로 추가

        for r in rows:
            labels = r.get("labels", []) or []
            label_counter.update(labels)
            n = r.get("n") or {}

            if "Contract" in labels:
                contracts.append({
                    "contractId": n.get("contractId"),
                    "amount": n.get("amount"),
                    "value_ccy": n.get("value_ccy"),
                    "award_date": n.get("award_date"),
                })

            if "Company" in labels:
                company_info = {
                    "name": n.get("name"),
                    "ticker": n.get("ticker"),
                    "market": n.get("market"),
                    "sector": n.get("sector"),
                    "market_cap": n.get("market_cap"),
                    "is_listed": n.get("is_listed", False),
                }
                if company_info["name"]:
                    companies.append(company_info)

            if "Program" in labels:
                name = n.get("label") or n.get("code")
                if name:
                    programs.append(name)

            if "Product" in labels:  # 새로 추가
                name = n.get("name")
                if name:
                    products.append(name)

            # Product 또는 WeaponSystem (호환성 유지)
            if "WeaponSystem" in labels:
                name = n.get("label") or n.get("name") or n.get("productName")
                if name:
                    products.append(name)  # products로 통합
                    weapons.append(name)  # 호환성 유지

            if "FinancialMetric" in labels:  # 새로 추가
                financial_metrics.append({
                    "metric_type": n.get("metric_type"),
                    "amount": n.get("amount"),
                    "currency": n.get("currency"),
                    "period": n.get("period"),
                    "year_over_year": n.get("year_over_year"),
                })

            if "Investment" in labels:  # 새로 추가
                investments.append({
                    "investment_type": n.get("investment_type"),
                    "amount": n.get("amount"),
                    "currency": n.get("currency"),
                    "stake_percentage": n.get("stake_percentage"),
                    "purpose": n.get("purpose"),
                })

            if "Event" in labels:
                events_sample.append({
                    "event_type": n.get("event_type"),
                    "title": n.get("title"),
                    "published_at": _safe_dt(n.get("published_at")),
                    "sentiment": n.get("sentiment"),
                    "confidence": n.get("confidence"),
                })

        # 계약 합계/상위
        total_amt = 0.0
        for c in contracts:
            try:
                if c.get("amount") is not None:
                    total_amt += float(c["amount"])
            except Exception:
                pass

        top_contracts = sorted(
            contracts, key=lambda x: (x.get("amount") or 0), reverse=True
        )[:5]

        # 재무지표 분석
        total_revenue = 0.0
        total_operating_profit = 0.0
        for fm in financial_metrics:
            try:
                amount = float(fm.get("amount", 0))
                if fm.get("metric_type") == "revenue":
                    total_revenue += amount
                elif fm.get("metric_type") == "operating_profit":
                    total_operating_profit += amount
            except Exception:
                pass

        # 투자 분석
        total_investment = 0.0
        for inv in investments:
            try:
                if inv.get("amount") is not None:
                    total_investment += float(inv["amount"])
            except Exception:
                pass

        # 상장사 분석 (상장사 우선 정렬)
        listed_companies = [c for c in companies if c.get("is_listed")]
        unlisted_companies = [c for c in companies if not c.get("is_listed")]

        # 시가총액 기준 정렬
        listed_companies.sort(key=lambda x: x.get("market_cap", 0), reverse=True)

        # 회사명 리스트 (상장사 우선)
        company_names = ([c["name"] for c in listed_companies] +
                        [c["name"] for c in unlisted_companies])

        return {
            "label_distribution": label_counter.most_common(),
            "contract_total_amount": total_amt,
            "contract_top": top_contracts,
            "companies_top": [k for k, _ in Counter(company_names).most_common(8)],
            "listed_companies": listed_companies[:5],  # 상위 5개 상장사
            "programs_top": [k for k, _ in Counter(programs).most_common(8)],
            "weapons_top": [k for k, _ in Counter(products).most_common(8)],  # products 사용 (호환성)
            "products_top": [k for k, _ in Counter(products).most_common(8)],  # 새로 추가
            "events_sample": events_sample[:8],
            "financial_summary": {  # 새로 추가
                "total_revenue": total_revenue,
                "total_operating_profit": total_operating_profit,
                "revenue_companies": len([fm for fm in financial_metrics if fm.get("metric_type") == "revenue"]),
            },
            "investment_summary": {  # 새로 추가
                "total_amount": total_investment,
                "count": len(investments),
                "types": list(set([inv.get("investment_type") for inv in investments if inv.get("investment_type")])),
            },
        }