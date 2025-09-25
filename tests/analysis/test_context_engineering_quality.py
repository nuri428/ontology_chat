#!/usr/bin/env python3
"""
컨텍스트 엔지니어링 기반 질의 응답 품질 검증 시스템
- 다양한 복잡도와 주제의 테스트 질문 세트
- 응답 품질 평가 메트릭
- 개선 포인트 식별
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
from api.config import settings

@dataclass
class TestQuestion:
    """테스트 질문 정의"""
    id: str
    question: str
    category: str
    complexity: str  # simple, medium, complex
    expected_elements: List[str]  # 응답에 포함되어야 할 핵심 요소들
    evaluation_criteria: Dict[str, str]  # 평가 기준

@dataclass
class ResponseEvaluation:
    """응답 평가 결과"""
    question_id: str
    response_text: str
    response_time: float
    relevance_score: float  # 0-10
    completeness_score: float  # 0-10
    accuracy_score: float  # 0-10
    context_usage_score: float  # 0-10
    overall_score: float  # 0-10
    missing_elements: List[str]
    strengths: List[str]
    weaknesses: List[str]
    improvement_suggestions: List[str]

class ContextEngineeringQualityTester:
    """컨텍스트 엔지니어링 품질 테스터"""

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

    def create_test_questions(self) -> List[TestQuestion]:
        """다양한 복잡도와 주제의 테스트 질문 생성"""
        questions = [
            # === 단순 질문 (Simple) ===
            TestQuestion(
                id="simple_01",
                question="삼성전자 주가는 어떻게 되나요?",
                category="주식정보",
                complexity="simple",
                expected_elements=["삼성전자", "주가", "현재 가격", "등락률"],
                evaluation_criteria={
                    "relevance": "삼성전자 주가 정보 직접 제공",
                    "completeness": "현재가, 등락률, 거래량 등 기본 정보",
                    "accuracy": "최신 주가 데이터 정확성"
                }
            ),

            TestQuestion(
                id="simple_02",
                question="오늘 주요 뉴스가 뭐가 있나요?",
                category="뉴스정보",
                complexity="simple",
                expected_elements=["오늘", "주요 뉴스", "헤드라인", "요약"],
                evaluation_criteria={
                    "relevance": "당일 주요 뉴스 제공",
                    "completeness": "다양한 분야 뉴스 포괄",
                    "accuracy": "최신성과 정확성"
                }
            ),

            # === 중간 복잡도 질문 (Medium) ===
            TestQuestion(
                id="medium_01",
                question="반도체 업계의 최근 동향과 관련 주식들의 전망은 어떤가요?",
                category="산업분석",
                complexity="medium",
                expected_elements=["반도체 업계", "최근 동향", "관련 주식", "전망", "분석"],
                evaluation_criteria={
                    "relevance": "반도체 업계 동향과 주식 연결 분석",
                    "completeness": "업계 현황, 주요 기업, 전망 종합 제공",
                    "accuracy": "업계 전문 지식과 최신 정보 결합"
                }
            ),

            TestQuestion(
                id="medium_02",
                question="미국 금리 인상이 한국 경제와 주식시장에 미치는 영향을 분석해주세요",
                category="경제분석",
                complexity="medium",
                expected_elements=["미국 금리", "한국 경제", "주식시장", "영향 분석", "인과관계"],
                evaluation_criteria={
                    "relevance": "금리-경제-주식 연관성 분석",
                    "completeness": "거시경제적 영향과 구체적 시장 반응",
                    "accuracy": "경제학적 논리와 실제 데이터 기반"
                }
            ),

            TestQuestion(
                id="medium_03",
                question="ESG 투자가 주목받는 이유와 관련 유망 종목들을 추천해주세요",
                category="투자전략",
                complexity="medium",
                expected_elements=["ESG 투자", "주목받는 이유", "유망 종목", "추천 근거"],
                evaluation_criteria={
                    "relevance": "ESG 투자 트렌드와 종목 연결",
                    "completeness": "ESG 개념, 시장 동향, 구체적 종목",
                    "accuracy": "ESG 평가 기준과 종목 정보 정확성"
                }
            ),

            # === 복합 질문 (Complex) ===
            TestQuestion(
                id="complex_01",
                question="최근 글로벌 공급망 이슈와 인플레이션 우려가 IT 대기업들의 실적과 주가에 어떤 영향을 미치고 있으며, 향후 6개월간 투자 전략은 어떻게 수립해야 할까요?",
                category="종합분석",
                complexity="complex",
                expected_elements=["공급망 이슈", "인플레이션", "IT 대기업", "실적 영향", "주가 영향", "투자 전략", "6개월 전망"],
                evaluation_criteria={
                    "relevance": "다중 요인 분석과 투자 전략 연결",
                    "completeness": "거시 이슈, 기업 분석, 전략 제시",
                    "accuracy": "복합적 인과관계 정확한 분석"
                }
            ),

            TestQuestion(
                id="complex_02",
                question="탄소중립 정책이 전통 제조업체들의 사업 모델 변화를 어떻게 유도하고 있으며, 이 과정에서 새로운 투자 기회와 리스크는 무엇인지 구체적인 기업 사례와 함께 분석해주세요",
                category="정책분석",
                complexity="complex",
                expected_elements=["탄소중립", "제조업체", "사업모델 변화", "투자 기회", "리스크", "기업 사례"],
                evaluation_criteria={
                    "relevance": "정책-기업-투자 다층 분석",
                    "completeness": "정책 배경, 기업 대응, 투자 관점",
                    "accuracy": "실제 기업 사례와 데이터 기반"
                }
            ),

            # === 추상적 질문 ===
            TestQuestion(
                id="abstract_01",
                question="디지털 전환이 가속화되는 시대에 '가치 투자'의 의미와 방법론은 어떻게 진화해야 할까요?",
                category="투자철학",
                complexity="complex",
                expected_elements=["디지털 전환", "가치 투자", "의미 진화", "방법론 변화"],
                evaluation_criteria={
                    "relevance": "시대 변화와 투자 철학 연결",
                    "completeness": "개념 정의, 변화 요인, 새로운 접근법",
                    "accuracy": "투자 이론과 현실 적용 정확성"
                }
            ),

            # === 시계열 분석 질문 ===
            TestQuestion(
                id="timeseries_01",
                question="지난 3년간 코스피 지수의 변동 패턴과 주요 이벤트들의 영향을 분석하고, 향후 1년간의 시장 방향성을 예측해주세요",
                category="시장분석",
                complexity="complex",
                expected_elements=["3년간", "코스피", "변동 패턴", "주요 이벤트", "영향 분석", "1년 예측"],
                evaluation_criteria={
                    "relevance": "과거 패턴과 미래 예측 연결",
                    "completeness": "역사적 분석과 예측 근거",
                    "accuracy": "데이터 기반 분석과 합리적 예측"
                }
            )
        ]

        return questions

    async def run_test(self, question: TestQuestion) -> Tuple[str, float]:
        """개별 질문 테스트 실행"""
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

    def evaluate_response(self, question: TestQuestion, response: str, response_time: float) -> ResponseEvaluation:
        """응답 품질 평가"""

        # 기본 평가 점수 초기화
        relevance_score = 0
        completeness_score = 0
        accuracy_score = 0
        context_usage_score = 0

        missing_elements = []
        strengths = []
        weaknesses = []
        suggestions = []

        response_lower = response.lower()

        # === 관련성 평가 (Relevance) ===
        expected_count = 0
        for element in question.expected_elements:
            if element.lower() in response_lower:
                expected_count += 1
            else:
                missing_elements.append(element)

        relevance_score = (expected_count / len(question.expected_elements)) * 10

        # === 완성도 평가 (Completeness) ===
        if len(response) < 50:
            completeness_score = 2
            weaknesses.append("응답이 너무 짧음")
        elif len(response) < 200:
            completeness_score = 5
            suggestions.append("더 상세한 설명 필요")
        elif len(response) < 500:
            completeness_score = 7
            strengths.append("적절한 분량")
        else:
            completeness_score = 9
            strengths.append("충분히 상세한 응답")

        # === 정확성 평가 (Accuracy) ===
        if "ERROR" in response or "오류" in response or "실패" in response:
            accuracy_score = 1
            weaknesses.append("시스템 오류 발생")
        elif "죄송" in response or "알 수 없" in response:
            accuracy_score = 3
            weaknesses.append("정보 부족으로 답변 제한")
        elif "추정" in response or "예상" in response:
            accuracy_score = 6
            strengths.append("불확실성 명시")
        else:
            accuracy_score = 8
            strengths.append("확신있는 답변")

        # === 컨텍스트 활용도 평가 ===
        context_indicators = ["최근", "현재", "오늘", "실시간", "업데이트", "분석", "데이터"]
        context_count = sum(1 for indicator in context_indicators if indicator in response_lower)
        context_usage_score = min(context_count * 1.5, 10)

        if context_count >= 3:
            strengths.append("컨텍스트 정보 잘 활용")
        else:
            suggestions.append("더 많은 컨텍스트 정보 활용 필요")

        # === 복잡도별 추가 평가 ===
        if question.complexity == "complex":
            if "따라서" in response or "그러므로" in response or "결론적으로" in response:
                strengths.append("논리적 결론 제시")
            else:
                suggestions.append("분석 결과의 논리적 결론 필요")

        # === 전체 점수 계산 ===
        overall_score = (relevance_score * 0.3 +
                        completeness_score * 0.25 +
                        accuracy_score * 0.25 +
                        context_usage_score * 0.2)

        # 응답 시간 패널티
        if response_time > 10:
            weaknesses.append(f"응답 시간 너무 길음 ({response_time:.1f}초)")
            overall_score *= 0.9
        elif response_time > 5:
            suggestions.append("응답 시간 최적화 필요")
            overall_score *= 0.95

        return ResponseEvaluation(
            question_id=question.id,
            response_text=response,
            response_time=response_time,
            relevance_score=relevance_score,
            completeness_score=completeness_score,
            accuracy_score=accuracy_score,
            context_usage_score=context_usage_score,
            overall_score=overall_score,
            missing_elements=missing_elements,
            strengths=strengths,
            weaknesses=weaknesses,
            improvement_suggestions=suggestions
        )

    async def run_comprehensive_test(self) -> List[ResponseEvaluation]:
        """종합 테스트 실행"""
        await self.initialize_services()

        questions = self.create_test_questions()
        evaluations = []

        print(f"\n🚀 컨텍스트 엔지니어링 품질 테스트 시작 ({len(questions)}개 질문)")
        print("=" * 80)

        for i, question in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] {question.complexity.upper()} - {question.category}")
            print(f"Q: {question.question}")
            print("-" * 60)

            response, response_time = await self.run_test(question)
            evaluation = self.evaluate_response(question, response, response_time)
            evaluations.append(evaluation)

            print(f"응답시간: {response_time:.2f}초")
            print(f"종합점수: {evaluation.overall_score:.1f}/10")
            print(f"세부점수: 관련성({evaluation.relevance_score:.1f}) "
                  f"완성도({evaluation.completeness_score:.1f}) "
                  f"정확성({evaluation.accuracy_score:.1f}) "
                  f"컨텍스트({evaluation.context_usage_score:.1f})")

            if evaluation.strengths:
                print(f"✅ 강점: {', '.join(evaluation.strengths)}")
            if evaluation.weaknesses:
                print(f"⚠️ 약점: {', '.join(evaluation.weaknesses)}")

            # 응답 미리보기 (처음 200자)
            preview = response[:200] + ("..." if len(response) > 200 else "")
            print(f"응답: {preview}")

        return evaluations

    def generate_comprehensive_report(self, evaluations: List[ResponseEvaluation]) -> Dict[str, Any]:
        """종합 분석 보고서 생성"""
        if not evaluations:
            return {"error": "평가 결과가 없습니다"}

        # 기본 통계
        overall_scores = [e.overall_score for e in evaluations]
        avg_score = statistics.mean(overall_scores)
        median_score = statistics.median(overall_scores)

        # 복잡도별 분석
        complexity_analysis = {}
        for complexity in ["simple", "medium", "complex"]:
            complex_evals = [e for e in evaluations if complexity in e.question_id]
            if complex_evals:
                complexity_analysis[complexity] = {
                    "count": len(complex_evals),
                    "avg_score": statistics.mean([e.overall_score for e in complex_evals]),
                    "avg_time": statistics.mean([e.response_time for e in complex_evals])
                }

        # 주요 문제점 집계
        all_weaknesses = []
        all_suggestions = []
        missing_elements_count = {}

        for eval in evaluations:
            all_weaknesses.extend(eval.weaknesses)
            all_suggestions.extend(eval.improvement_suggestions)
            for element in eval.missing_elements:
                missing_elements_count[element] = missing_elements_count.get(element, 0) + 1

        # 빈도수 기준 상위 문제점
        weakness_frequency = {}
        for weakness in all_weaknesses:
            weakness_frequency[weakness] = weakness_frequency.get(weakness, 0) + 1

        top_weaknesses = sorted(weakness_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
        top_missing_elements = sorted(missing_elements_count.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "summary": {
                "total_questions": len(evaluations),
                "average_score": round(avg_score, 2),
                "median_score": round(median_score, 2),
                "score_distribution": {
                    "excellent (9-10)": sum(1 for s in overall_scores if s >= 9),
                    "good (7-8.9)": sum(1 for s in overall_scores if 7 <= s < 9),
                    "average (5-6.9)": sum(1 for s in overall_scores if 5 <= s < 7),
                    "poor (0-4.9)": sum(1 for s in overall_scores if s < 5)
                }
            },
            "complexity_analysis": complexity_analysis,
            "top_issues": {
                "frequent_weaknesses": top_weaknesses,
                "commonly_missing_elements": top_missing_elements
            },
            "improvement_priorities": list(set(all_suggestions)),
            "detailed_results": [asdict(e) for e in evaluations]
        }

async def main():
    """메인 실행 함수"""
    tester = ContextEngineeringQualityTester()

    try:
        # 종합 테스트 실행
        evaluations = await tester.run_comprehensive_test()

        # 보고서 생성
        report = tester.generate_comprehensive_report(evaluations)

        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"/data/dev/git/ontology_chat/context_quality_report_{timestamp}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📊 종합 분석 결과")
        print("=" * 80)
        print(f"전체 평균 점수: {report['summary']['average_score']}/10")
        print(f"점수 분포:")
        for grade, count in report['summary']['score_distribution'].items():
            print(f"  - {grade}: {count}개")

        if report['complexity_analysis']:
            print(f"\n복잡도별 성능:")
            for complexity, analysis in report['complexity_analysis'].items():
                print(f"  - {complexity}: {analysis['avg_score']:.1f}점 (평균 {analysis['avg_time']:.1f}초)")

        print(f"\n주요 개선 포인트:")
        for i, (issue, count) in enumerate(report['top_issues']['frequent_weaknesses'][:3], 1):
            print(f"  {i}. {issue} ({count}회)")

        print(f"\n상세 보고서: {report_file}")

        return report

    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(main())