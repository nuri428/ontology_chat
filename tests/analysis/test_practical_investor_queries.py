#!/usr/bin/env python3
"""
실용적 투자자 질의 테스트 시스템
- 실제 투자자가 자주 하는 질문들
- 특정 사안, 종목, 뉴스, 실적 관련 질의
- 품질 향상 포인트 도출
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics

# 프로젝트 모듈들
from api.services.chat_service import ChatService
from api.services.enhanced_chat_service import EnhancedChatService

@dataclass
class PracticalTestQuestion:
    """실용적 테스트 질문"""
    id: str
    question: str
    category: str
    query_type: str  # news, performance, recent_issues, product_launch, analysis
    expected_content: List[str]  # 응답에 포함되어야 할 핵심 내용
    evaluation_focus: List[str]  # 평가 중점 사항
    target_response_time: float = 3.0  # 목표 응답 시간(초)

@dataclass
class PracticalEvaluation:
    """실용적 평가 결과"""
    question_id: str
    response_text: str
    response_time: float

    # 실용적 평가 지표
    relevance_score: float  # 관련성 (0-10)
    timeliness_score: float  # 시의성 (0-10)
    specificity_score: float  # 구체성 (0-10)
    actionable_score: float  # 실행가능성 (0-10)
    data_richness_score: float  # 데이터 풍부성 (0-10)
    overall_score: float  # 종합점수 (0-10)

    missing_content: List[str]
    strengths: List[str]
    weaknesses: List[str]
    improvement_suggestions: List[str]

class PracticalInvestorQueryTester:
    """실용적 투자자 질의 테스터"""

    def __init__(self):
        self.chat_service = None
        self.enhanced_chat_service = None
        self.test_results = []

    async def initialize_services(self):
        """서비스 초기화"""
        try:
            self.enhanced_chat_service = EnhancedChatService()
            print("✅ Enhanced Chat Service 초기화 완료")
        except Exception as e:
            print(f"⚠️ Enhanced Chat Service 초기화 실패: {e}")
            try:
                self.chat_service = ChatService()
                print("✅ Basic Chat Service 초기화 완료")
            except Exception as e2:
                print(f"❌ Chat Service 초기화 실패: {e2}")
                raise

    def create_practical_questions(self) -> List[PracticalTestQuestion]:
        """실제 투자자들이 자주 하는 질문들"""
        questions = [
            # === 뉴스 조회 관련 ===
            PracticalTestQuestion(
                id="news_01",
                question="삼성전자 관련 최근 뉴스 중에서 주가에 영향을 줄만한 뉴스가 있나요?",
                category="뉴스조회",
                query_type="news",
                expected_content=["삼성전자", "최근 뉴스", "주가 영향", "구체적 뉴스 제목"],
                evaluation_focus=["최신성", "주가 연관성", "구체성"],
                target_response_time=2.0
            ),

            PracticalTestQuestion(
                id="news_02",
                question="반도체 업계에서 오늘 발표된 중요한 뉴스는 무엇인가요?",
                category="뉴스조회",
                query_type="news",
                expected_content=["반도체", "오늘", "중요 뉴스", "업계 동향"],
                evaluation_focus=["당일성", "업계 특화", "중요도 판별"],
                target_response_time=2.0
            ),

            # === 실적 관련 ===
            PracticalTestQuestion(
                id="performance_01",
                question="최근 매출이 크게 오른 종목들을 추천해주세요",
                category="실적분석",
                query_type="performance",
                expected_content=["매출 증가", "종목 추천", "구체적 회사명", "증가율"],
                evaluation_focus=["실적 데이터", "종목 선별", "추천 근거"],
                target_response_time=3.0
            ),

            PracticalTestQuestion(
                id="performance_02",
                question="3분기 실적이 예상보다 좋았던 회사들은 어디인가요?",
                category="실적분석",
                query_type="performance",
                expected_content=["3분기", "실적", "예상 대비", "회사명"],
                evaluation_focus=["분기별 데이터", "예상치 비교", "실적 서프라이즈"],
                target_response_time=3.0
            ),

            # === 최근 이슈 종목 ===
            PracticalTestQuestion(
                id="issues_01",
                question="최근 이슈가 되는 종목은 무엇이고 이유는 뭔가요?",
                category="이슈분석",
                query_type="recent_issues",
                expected_content=["최근 이슈", "종목명", "이슈 이유", "시장 반응"],
                evaluation_focus=["이슈 파악", "원인 분석", "시의성"],
                target_response_time=2.5
            ),

            PracticalTestQuestion(
                id="issues_02",
                question="급등한 종목들의 급등 이유를 분석해주세요",
                category="이슈분석",
                query_type="recent_issues",
                expected_content=["급등 종목", "급등 이유", "분석", "주가 변동"],
                evaluation_focus=["급등 종목 식별", "원인 분석", "논리적 설명"],
                target_response_time=3.0
            ),

            # === 제품 발표 관련 ===
            PracticalTestQuestion(
                id="product_01",
                question="아이온2 발표에 대한 NC소프트의 전망은 어떤가요?",
                category="제품발표",
                query_type="product_launch",
                expected_content=["아이온2", "NC소프트", "전망", "게임 산업"],
                evaluation_focus=["특정 제품 정보", "회사별 영향", "전망 분석"],
                target_response_time=2.5
            ),

            PracticalTestQuestion(
                id="product_02",
                question="최근 발표된 신제품이 주가에 긍정적 영향을 준 회사는?",
                category="제품발표",
                query_type="product_launch",
                expected_content=["신제품 발표", "주가 상승", "회사명", "제품 정보"],
                evaluation_focus=["신제품 식별", "주가 연관성", "영향 분석"],
                target_response_time=3.0
            ),

            # === 특정 분야 분석 ===
            PracticalTestQuestion(
                id="analysis_01",
                question="2차전지 관련주 중에서 올해 실적이 가장 좋은 회사는?",
                category="분야분석",
                query_type="analysis",
                expected_content=["2차전지", "관련주", "올해 실적", "회사 비교"],
                evaluation_focus=["섹터 분석", "실적 비교", "순위 선정"],
                target_response_time=3.5
            ),

            PracticalTestQuestion(
                id="analysis_02",
                question="K-뷰티 관련 종목들의 해외 진출 성과는 어떤가요?",
                category="분야분석",
                query_type="analysis",
                expected_content=["K-뷰티", "관련 종목", "해외 진출", "성과 분석"],
                evaluation_focus=["테마주 파악", "해외 실적", "성과 측정"],
                target_response_time=3.5
            ),

            # === 시황 분석 ===
            PracticalTestQuestion(
                id="market_01",
                question="오늘 코스피가 오른 이유와 상승 주도주는 무엇인가요?",
                category="시황분석",
                query_type="market_analysis",
                expected_content=["코스피", "상승 이유", "주도주", "시장 동향"],
                evaluation_focus=["당일 시황", "상승 요인", "주도주 식별"],
                target_response_time=2.0
            ),
        ]

        return questions

    async def run_practical_test(self, question: PracticalTestQuestion) -> Tuple[str, float]:
        """실용적 질문 테스트 실행"""
        start_time = time.time()

        try:
            if self.enhanced_chat_service:
                response = await self.enhanced_chat_service.generate_answer(question.question)
            else:
                response = await self.chat_service.generate_answer(question.question)

            response_time = time.time() - start_time

            # 응답 구조에 따라 텍스트 추출
            if isinstance(response, dict):
                response_text = response.get("answer", "") or response.get("markdown", "") or response.get("response", "")
            else:
                response_text = str(response)

            return response_text, response_time

        except Exception as e:
            response_time = time.time() - start_time
            return f"ERROR: {str(e)}", response_time

    def evaluate_practical_response(
        self,
        question: PracticalTestQuestion,
        response: str,
        response_time: float
    ) -> PracticalEvaluation:
        """실용적 관점에서 응답 평가"""

        response_lower = response.lower()
        missing_content = []
        strengths = []
        weaknesses = []
        suggestions = []

        # === 관련성 평가 ===
        expected_found = 0
        for content in question.expected_content:
            if content.lower() in response_lower:
                expected_found += 1
            else:
                missing_content.append(content)

        relevance_score = (expected_found / len(question.expected_content)) * 10

        # === 시의성 평가 ===
        timeliness_indicators = ["최근", "오늘", "어제", "이번주", "3분기", "올해", "2024", "발표", "공시"]
        timeliness_count = sum(1 for indicator in timeliness_indicators if indicator in response_lower)
        timeliness_score = min(timeliness_count * 2, 10)

        if timeliness_score >= 6:
            strengths.append("시의성 정보 포함")
        else:
            weaknesses.append("시의성 정보 부족")
            suggestions.append("최신 정보 및 구체적 시점 명시 필요")

        # === 구체성 평가 ===
        specific_indicators = 0

        # 회사명, 종목명 언급
        company_patterns = ["삼성", "LG", "SK", "현대", "포스코", "네이버", "카카오", "NC소프트", "셀트리온"]
        company_mentions = sum(1 for company in company_patterns if company in response)
        specific_indicators += min(company_mentions, 3)

        # 숫자, 수치 언급
        import re
        numbers = re.findall(r'\d+(?:\.\d+)?%|\d+(?:,\d+)*(?:\.\d+)?[원억만조]|\d+(?:\.\d+)?배', response)
        specific_indicators += min(len(numbers), 3)

        # 구체적 제품명, 서비스명
        if any(term in response for term in ["아이온", "제품", "서비스", "기술"]):
            specific_indicators += 1

        specificity_score = min(specific_indicators * 1.5, 10)

        # === 실행가능성 평가 ===
        actionable_indicators = ["추천", "전망", "예상", "목표", "전략", "투자", "매수", "매도", "보유"]
        actionable_count = sum(1 for indicator in actionable_indicators if indicator in response_lower)
        actionable_score = min(actionable_count * 2, 10)

        if actionable_score >= 6:
            strengths.append("투자 실행 관련 정보 제공")
        else:
            suggestions.append("구체적 투자 관점이나 실행 가능한 정보 추가 필요")

        # === 데이터 풍부성 평가 ===
        data_indicators = 0

        # 뉴스 인용
        if any(term in response for term in ["뉴스", "발표", "공시", "보고서"]):
            data_indicators += 2

        # 실적 데이터
        if any(term in response for term in ["매출", "영업이익", "실적", "분기"]):
            data_indicators += 2

        # 주가 정보
        if any(term in response for term in ["주가", "주식", "상승", "하락", "등락"]):
            data_indicators += 1

        # 구체적 출처
        if any(term in response for term in ["according to", "보고서에 따르면", "발표에 의하면"]):
            data_indicators += 1

        data_richness_score = min(data_indicators * 1.5, 10)

        # === 응답 시간 평가 ===
        time_penalty = 1.0
        if response_time > question.target_response_time * 2:
            time_penalty = 0.7
            weaknesses.append(f"응답 시간 과다 ({response_time:.1f}초)")
        elif response_time > question.target_response_time:
            time_penalty = 0.85
            suggestions.append("응답 속도 개선 필요")
        else:
            strengths.append(f"빠른 응답 속도 ({response_time:.1f}초)")

        # === ERROR 처리 ===
        if "ERROR" in response or "오류" in response:
            relevance_score *= 0.1
            actionable_score = 0
            weaknesses.append("시스템 오류 발생")

        # === 종합 점수 계산 ===
        overall_score = (
            relevance_score * 0.25 +      # 관련성 25%
            timeliness_score * 0.20 +     # 시의성 20%
            specificity_score * 0.20 +    # 구체성 20%
            actionable_score * 0.20 +     # 실행가능성 20%
            data_richness_score * 0.15    # 데이터 풍부성 15%
        ) * time_penalty

        # 카테고리별 추가 평가
        if question.query_type == "news" and "뉴스" not in response_lower:
            weaknesses.append("뉴스 정보 부족")
            overall_score *= 0.8

        if question.query_type == "performance" and not any(term in response_lower for term in ["실적", "매출", "수익"]):
            weaknesses.append("실적 정보 부족")
            overall_score *= 0.8

        return PracticalEvaluation(
            question_id=question.id,
            response_text=response,
            response_time=response_time,
            relevance_score=relevance_score,
            timeliness_score=timeliness_score,
            specificity_score=specificity_score,
            actionable_score=actionable_score,
            data_richness_score=data_richness_score,
            overall_score=overall_score,
            missing_content=missing_content,
            strengths=strengths,
            weaknesses=weaknesses,
            improvement_suggestions=suggestions
        )

    async def run_comprehensive_practical_test(self) -> List[PracticalEvaluation]:
        """종합 실용적 테스트 실행"""
        await self.initialize_services()

        questions = self.create_practical_questions()
        evaluations = []

        print(f"\n🎯 실용적 투자자 질의 테스트 시작 ({len(questions)}개 질문)")
        print("=" * 80)

        for i, question in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] {question.query_type.upper()} - {question.category}")
            print(f"Q: {question.question}")
            print(f"목표 시간: {question.target_response_time}초")
            print("-" * 60)

            response, response_time = await self.run_practical_test(question)
            evaluation = self.evaluate_practical_response(question, response, response_time)
            evaluations.append(evaluation)

            # 결과 출력
            print(f"⏱️ 응답시간: {response_time:.2f}초 (목표: {question.target_response_time}초)")
            print(f"🎯 종합점수: {evaluation.overall_score:.1f}/10")
            print(f"📊 세부점수: 관련성({evaluation.relevance_score:.1f}) "
                  f"시의성({evaluation.timeliness_score:.1f}) "
                  f"구체성({evaluation.specificity_score:.1f}) "
                  f"실행성({evaluation.actionable_score:.1f}) "
                  f"데이터({evaluation.data_richness_score:.1f})")

            if evaluation.strengths:
                print(f"✅ 강점: {', '.join(evaluation.strengths)}")
            if evaluation.weaknesses:
                print(f"⚠️ 약점: {', '.join(evaluation.weaknesses)}")
            if evaluation.missing_content:
                print(f"❌ 누락: {', '.join(evaluation.missing_content)}")

            # 응답 미리보기
            preview = response[:150] + ("..." if len(response) > 150 else "")
            print(f"💬 응답: {preview}")

        return evaluations

    def generate_practical_improvement_report(self, evaluations: List[PracticalEvaluation]) -> Dict[str, Any]:
        """실용적 개선 보고서 생성"""
        if not evaluations:
            return {"error": "평가 결과가 없습니다"}

        # 기본 통계
        overall_scores = [e.overall_score for e in evaluations]
        avg_score = statistics.mean(overall_scores)

        # 카테고리별 분석
        category_stats = {}
        query_type_stats = {}

        for eval in evaluations:
            # 카테고리 추출 (question_id에서)
            category = eval.question_id.split('_')[0]
            if category not in category_stats:
                category_stats[category] = []
            category_stats[category].append(eval.overall_score)

        for category, scores in category_stats.items():
            query_type_stats[category] = {
                "평균점수": round(statistics.mean(scores), 2),
                "문제수": len(scores),
                "평균응답시간": round(statistics.mean([e.response_time for e in evaluations if e.question_id.startswith(category)]), 2)
            }

        # 주요 문제점 집계
        all_weaknesses = []
        all_suggestions = []
        all_missing = []

        for eval in evaluations:
            all_weaknesses.extend(eval.weaknesses)
            all_suggestions.extend(eval.improvement_suggestions)
            all_missing.extend(eval.missing_content)

        # 빈도 분석
        weakness_freq = {}
        for weakness in all_weaknesses:
            weakness_freq[weakness] = weakness_freq.get(weakness, 0) + 1

        missing_freq = {}
        for missing in all_missing:
            missing_freq[missing] = missing_freq.get(missing, 0) + 1

        top_weaknesses = sorted(weakness_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        top_missing = sorted(missing_freq.items(), key=lambda x: x[1], reverse=True)[:5]

        # 성능 분석
        response_times = [e.response_time for e in evaluations]
        slow_responses = [e for e in evaluations if e.response_time > 3.0]

        return {
            "summary": {
                "총_질문수": len(evaluations),
                "평균점수": round(avg_score, 2),
                "평균_응답시간": round(statistics.mean(response_times), 2),
                "목표시간_초과": len(slow_responses),
                "성능_등급": "우수" if avg_score >= 8 else "양호" if avg_score >= 6 else "개선필요"
            },
            "카테고리별_성능": query_type_stats,
            "주요_문제점": {
                "빈발_약점": top_weaknesses,
                "자주_누락되는_내용": top_missing,
                "느린_응답": [{"질문": e.question_id, "시간": e.response_time} for e in slow_responses]
            },
            "개선_우선순위": {
                "1순위": "뉴스 정보 제공 강화" if any("뉴스" in w[0] for w in top_weaknesses) else "응답 속도 개선",
                "2순위": "구체적 종목명 및 수치 정보 강화",
                "3순위": "실적 데이터 연계 개선",
                "4순위": "시의성 정보 강화",
                "5순위": "실행 가능한 투자 정보 제공"
            },
            "상세_결과": [asdict(e) for e in evaluations]
        }

async def main():
    """메인 실행"""
    tester = PracticalInvestorQueryTester()

    try:
        # 실용적 테스트 실행
        evaluations = await tester.run_comprehensive_practical_test()

        # 개선 보고서 생성
        report = tester.generate_practical_improvement_report(evaluations)

        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"/data/dev/git/ontology_chat/practical_investor_report_{timestamp}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 요약 출력
        print(f"\n📊 실용적 투자자 질의 테스트 결과")
        print("=" * 80)
        print(f"📈 평균 점수: {report['summary']['평균점수']}/10")
        print(f"⏱️ 평균 응답시간: {report['summary']['평균_응답시간']:.1f}초")
        print(f"🎯 성능 등급: {report['summary']['성능_등급']}")

        print(f"\n🏆 카테고리별 성능:")
        for category, stats in report['카테고리별_성능'].items():
            print(f"  - {category}: {stats['평균점수']}점 ({stats['평균응답시간']:.1f}초)")

        print(f"\n⚠️ 주요 개선 필요 사항:")
        for i, (issue, count) in enumerate(report['주요_문제점']['빈발_약점'][:3], 1):
            print(f"  {i}. {issue} ({count}회)")

        print(f"\n🎯 개선 우선순위:")
        for priority, action in report['개선_우선순위'].items():
            print(f"  {priority}: {action}")

        print(f"\n📁 상세 보고서: {report_file}")

        return report

    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(main())