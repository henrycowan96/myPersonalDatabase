import pytest
from unittest.mock import patch, Mock, AsyncMock
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from insights_engine import InsightsEngine
from insights_models import Insight, InsightType


class TestInsightsEngine:
    """Test class for insights engine functionality"""

    @pytest.fixture
    def mock_insights_engine(self, mock_pinecone, mock_openai):
        """Create insights engine with mocked dependencies"""
        _, mock_index = mock_pinecone
        
        with patch('insights_engine.utils') as mock_utils:
            mock_utils.pinecone_index = mock_index
            mock_utils.llm = Mock()
            mock_utils.llm.chat.completions.create.return_value = Mock(
                choices=[Mock(message=Mock(content="Test insight"))]
            )
            
            engine = InsightsEngine()
            yield engine

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generate_life_insights(self, mock_insights_engine):
        """Test generation of life insights"""
        # Mock data for insight generation
        user_data = {
            "recent_events": [
                {"type": "calendar_event", "content": "Job interview at Tech Corp"},
                {"type": "email", "content": "Offer letter from Tech Corp"}
            ],
            "timeframe": "30d"
        }
        
        insights = await mock_insights_engine.generate_insights("test-user", user_data)
        
        assert len(insights) > 0
        assert all(isinstance(insight, Insight) for insight in insights)
        assert all(insight.user_id == "test-user" for insight in insights)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generate_career_insights(self, mock_insights_engine):
        """Test generation of career-specific insights"""
        career_data = {
            "job_applications": 5,
            "interviews": 3,
            "networking_events": 2,
            "skill_development": ["Python", "Machine Learning"]
        }
        
        insights = await mock_insights_engine.generate_career_insights(
            "test-user", career_data
        )
        
        assert len(insights) > 0
        career_insights = [i for i in insights if i.insight_type == InsightType.CAREER]
        assert len(career_insights) > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generate_health_insights(self, mock_insights_engine):
        """Test generation of health-related insights"""
        health_data = {
            "exercise_sessions": 12,
            "sleep_hours_avg": 7.5,
            "stress_indicators": ["high workload", "poor sleep quality"],
            "medical_appointments": 1
        }
        
        insights = await mock_insights_engine.generate_health_insights(
            "test-user", health_data
        )
        
        assert len(insights) > 0
        health_insights = [i for i in insights if i.insight_type == InsightType.HEALTH]
        assert len(health_insights) > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generate_relationship_insights(self, mock_insights_engine):
        """Test generation of relationship insights"""
        relationship_data = {
            "social_events": 8,
            "communication_frequency": "high",
            "close_contacts": 15,
            "new_connections": 3
        }
        
        insights = await mock_insights_engine.generate_relationship_insights(
            "test-user", relationship_data
        )
        
        assert len(insights) > 0
        rel_insights = [i for i in insights if i.insight_type == InsightType.RELATIONSHIP]
        assert len(rel_insights) > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generate_financial_insights(self, mock_insights_engine):
        """Test generation of financial insights"""
        financial_data = {
            "income_sources": ["salary", "freelance"],
            "major_expenses": ["rent", "utilities", "groceries"],
            "savings_rate": 0.15,
            "investment_activities": 4
        }
        
        insights = await mock_insights_engine.generate_financial_insights(
            "test-user", financial_data
        )
        
        assert len(insights) > 0
        fin_insights = [i for i in insights if i.insight_type == InsightType.FINANCIAL]
        assert len(fin_insights) > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_insight_personalization(self, mock_insights_engine):
        """Test that insights are personalized based on user preferences"""
        user_preferences = {
            "focus_areas": ["career", "health"],
            "insight_frequency": "weekly",
            "notification_preferences": ["email", "push"]
        }
        
        user_data = {
            "recent_events": [
                {"type": "calendar_event", "content": "Gym session"},
                {"type": "calendar_event", "content": "Project deadline"}
            ]
        }
        
        insights = await mock_insights_engine.generate_personalized_insights(
            "test-user", user_data, user_preferences
        )
        
        # Should prioritize career and health insights
        career_health_insights = [
            i for i in insights 
            if i.insight_type in [InsightType.CAREER, InsightType.HEALTH]
        ]
        assert len(career_health_insights) >= len(insights) // 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_insight_trend_analysis(self, mock_insights_engine):
        """Test trend analysis in insights"""
        historical_data = {
            "insights_history": [
                {"date": "2024-01-01", "stress_level": 7, "productivity": 6},
                {"date": "2024-01-08", "stress_level": 6, "productivity": 7},
                {"date": "2024-01-15", "stress_level": 5, "productivity": 8}
            ]
        }
        
        trends = await mock_insights_engine.analyze_trends("test-user", historical_data)
        
        assert "stress_trend" in trends
        assert "productivity_trend" in trends
        assert trends["stress_trend"] == "decreasing"
        assert trends["productivity_trend"] == "increasing"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_insight_quality_scoring(self, mock_insights_engine):
        """Test insight quality scoring"""
        test_insights = [
            Insight(
                id="1",
                user_id="test-user",
                content="You've been exercising regularly",
                insight_type=InsightType.HEALTH,
                confidence_score=0.9,
                data_sources=["calendar", "fitness_app"]
            ),
            Insight(
                id="2", 
                user_id="test-user",
                content="Maybe you should exercise",
                insight_type=InsightType.HEALTH,
                confidence_score=0.3,
                data_sources=["calendar"]
            )
        ]
        
        scored_insights = await mock_insights_engine.score_insights(test_insights)
        
        assert len(scored_insights) == 2
        assert scored_insights[0].quality_score > scored_insights[1].quality_score
        assert scored_insights[0].quality_score >= 0.8
        assert scored_insights[1].quality_score <= 0.5

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_insight_deduplication(self, mock_insights_engine):
        """Test that duplicate insights are removed"""
        duplicate_insights = [
            Insight(
                id="1",
                user_id="test-user",
                content="You exercise 3 times per week",
                insight_type=InsightType.HEALTH,
                confidence_score=0.8
            ),
            Insight(
                id="2",
                user_id="test-user",
                content="You exercise three times weekly",
                insight_type=InsightType.HEALTH,
                confidence_score=0.8
            )
        ]
        
        deduplicated = await mock_insights_engine.deduplicate_insights(duplicate_insights)
        
        assert len(deduplicated) == 1
        assert deduplicated[0].content in [i.content for i in duplicate_insights]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_insight_caching(self, mock_insights_engine):
        """Test insight caching mechanism"""
        user_data = {"recent_events": [{"type": "calendar_event", "content": "Test"}]}
        
        # Generate insights first time
        insights1 = await mock_insights_engine.generate_insights("test-user", user_data)
        
        # Generate insights second time (should use cache)
        insights2 = await mock_insights_engine.generate_insights("test-user", user_data)
        
        # Should return same insights quickly
        assert len(insights1) == len(insights2)
        assert insights1[0].content == insights2[0].content

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_insight_error_handling(self, mock_insights_engine):
        """Test error handling in insight generation"""
        # Mock LLM failure
        mock_insights_engine.llm.chat.completions.create.side_effect = Exception("LLM error")
        
        user_data = {"recent_events": [{"type": "calendar_event", "content": "Test"}]}
        
        insights = await mock_insights_engine.generate_insights("test-user", user_data)
        
        # Should handle error gracefully
        assert isinstance(insights, list)
        # Should return fallback insights or empty list
        assert all(isinstance(insight, Insight) for insight in insights) or len(insights) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_insight_data_validation(self, mock_insights_engine):
        """Test data validation for insight generation"""
        invalid_data = {
            "recent_events": "not a list",
            "timeframe": None,
            "user_preferences": {}
        }
        
        insights = await mock_insights_engine.generate_insights("test-user", invalid_data)
        
        # Should handle invalid data gracefully
        assert isinstance(insights, list)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_insight_multilingual_support(self, mock_insights_engine):
        """Test insight generation in different languages"""
        user_preferences = {"language": "es"}
        user_data = {
            "recent_events": [{"type": "calendar_event", "content": "Entrevista de trabajo"}]
        }
        
        insights = await mock_insights_engine.generate_insights(
            "test-user", user_data, user_preferences
        )
        
        assert len(insights) > 0
        # Should generate insights in Spanish
        assert any("spanish" in insight.content.lower() or "español" in insight.content.lower() 
                  for insight in insights)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_insight_privacy_filtering(self, mock_insights_engine):
        """Test that sensitive information is filtered from insights"""
        sensitive_data = {
            "recent_events": [
                {"type": "email", "content": "SSN: 123-45-6789", "sensitive": True},
                {"type": "calendar_event", "content": "Doctor appointment", "sensitive": False}
            ]
        }
        
        insights = await mock_insights_engine.generate_insights("test-user", sensitive_data)
        
        # Should not include sensitive information in insights
        for insight in insights:
            assert "123-45-6789" not in insight.content
            assert "ssn" not in insight.content.lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_insight_actionability(self, mock_insights_engine):
        """Test that insights include actionable recommendations"""
        user_data = {
            "recent_events": [
                {"type": "calendar_event", "content": "Missed workout"},
                {"type": "calendar_event", "content": "Late night work"}
            ]
        }
        
        insights = await mock_insights_engine.generate_insights("test-user", user_data)
        
        # Should include actionable insights
        actionable_insights = [i for i in insights if i.actionable is True]
        assert len(actionable_insights) > 0
        
        for insight in actionable_insights:
            assert insight.recommendation is not None
            assert len(insight.recommendation) > 0
