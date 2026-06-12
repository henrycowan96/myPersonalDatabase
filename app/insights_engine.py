"""
Insights Engine for Personal Database (Apple Notes)
Analyzes Apple Notes data to detect meaningful patterns, life events, and generate proactive insights
Customized for Apple Notes data source only.
"""

from datetime import datetime
from typing import List, Dict
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from insights_models import Insight
from sentiment_analyzer import SentimentAnalyzer
from life_event_detector import LifeEventDetector
from temporal_analyzer import TemporalAnalyzer
from significance_scorer import SignificanceScorer
from llm_analyzer import LLMInsightAnalyzer


class InsightsEngine:
    """Main engine for generating insights from user data"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.life_event_detector = LifeEventDetector()
        self.temporal_analyzer = TemporalAnalyzer()
        self.significance_scorer = SignificanceScorer()
        self.llm_analyzer = LLMInsightAnalyzer()
    
    def generate_insights(self, documents: List[Dict], user_id: str) -> List[Insight]:
        """Generate insights from Apple Notes using two-phase approach"""
        insights = []
        
        print(f"[INSIGHTS] Starting two-phase insights analysis for {len(documents)} Apple Notes")
        
        # === PHASE 1: Batch Title Analysis ===
        print("[INSIGHTS] Phase 1: Analyzing Apple Note titles for interests and patterns")
        title_analysis = self.llm_analyzer.analyze_document_titles_batch(documents)
        
        # Generate basic knowledge insights from title analysis
        if title_analysis:
            insights.extend(self._generate_knowledge_insights(title_analysis))
            print(f"[INSIGHTS] Phase 1 completed: {len(title_analysis)} categories analyzed")
        
        # === PHASE 2: Deep Document Analysis ===
        print("[INSIGHTS] Phase 2: Deep analysis of relevant Apple Notes")
        
        # Select documents for deep analysis based on Phase 1 results
        relevant_documents = self._select_documents_for_deep_analysis(documents, title_analysis)
        
        # Analyze selected documents
        scored_documents = []
        for doc in relevant_documents:
            text = doc.get('metadata', {}).get('text', '')
            sentiment = self.sentiment_analyzer.analyze(text)
            events = self.life_event_detector.detect_events(text, doc.get('metadata', {}))
            score = self.significance_scorer.score_document(doc, sentiment, events)
            
            scored_documents.append({
                'document': doc,
                'sentiment': sentiment,
                'events': events,
                'score': score
            })
        
        # Sort by significance
        scored_documents.sort(key=lambda x: x['score'], reverse=True)
        
        # Flag documents for LLM analysis (documents with events or high scores)
        flagged_documents = []
        for item in scored_documents:
            if (item['events'] and len(item['events']) > 0) or item['score'] > 0.6:
                flagged_documents.append(item['document'])
        
        # Get LLM insights from flagged documents
        llm_insights = []
        if flagged_documents:
            try:
                llm_insights = self.llm_analyzer.analyze_flagged_documents(flagged_documents[:5])  # Limit to 5 docs
                print(f"[INSIGHTS] Phase 2 LLM analysis: {len(llm_insights)} insights generated")
            except Exception as e:
                print(f"Error in LLM analysis: {e}")
        
        # Generate different types of insights from deep analysis
        insights.extend(self._generate_urgent_insights(scored_documents))
        insights.extend(self._generate_llm_milestone_insights(llm_insights))
        insights.extend(self._generate_milestone_insights(scored_documents))
        insights.extend(self._generate_trending_insights(scored_documents))
        insights.extend(self._generate_interesting_insights(scored_documents))

        # === NEW: Journaling Recommendations and Self-Discovery ===
        print("[INSIGHTS] Generating journaling recommendations and self-discovery insights")

        # Generate journaling recommendations
        journaling_recs = self.llm_analyzer.generate_journaling_recommendations(documents)
        if journaling_recs:
            insights.extend(self._generate_journaling_insights(journaling_recs))
            print(f"[INSIGHTS] Generated {len(journaling_recs)} journaling recommendations")

        # Generate self-discovery insights
        self_discovery = self.llm_analyzer.generate_self_discovery_insights(documents)
        if self_discovery:
            insights.extend(self._generate_self_discovery_insights(self_discovery))
            print(f"[INSIGHTS] Generated {len(self_discovery)} self-discovery insights")
        
        print(f"[INSIGHTS] Two-phase analysis complete: {len(insights)} total insights from Apple Notes")
        
        # Sort all insights by significance
        insights.sort(key=lambda x: x.significance_score, reverse=True)
        
        return insights[:20]  # Return top 20 insights
    
    def _generate_knowledge_insights(self, title_analysis: Dict) -> List[Insight]:
        """Generate insights from Apple Notes title analysis results"""
        insights = []
        
        # Generate insights for primary interests
        for interest_data in title_analysis.get('primary_interests', []):
            interest = interest_data.get('interest', 'Unknown Interest')
            confidence = interest_data.get('confidence', 'medium')
            explanation = interest_data.get('explanation', '')
            
            confidence_score = {'high': 0.9, 'medium': 0.6, 'low': 0.3}.get(confidence, 0.6)
            
            insight = Insight(
                id=f"knowledge_interest_{hash(interest) % 100000}",
                category='interesting',
                title=f"Primary Interest: {interest}",
                description=f"Based on Apple Note titles, you show strong interest in {interest}. {explanation}",
                significance_score=confidence_score * 0.8,
                sources=[],
                detected_at=datetime.now().isoformat(),
                time_context={'analysis_phase': 'title_batch', 'confidence': confidence},
                entities=[interest],
                actionable=False
            )
            insights.append(insight)
        
        # Generate insights for life areas
        for area_data in title_analysis.get('life_areas', []):
            area = area_data.get('area', 'Unknown Area')
            confidence = area_data.get('confidence', 'medium')
            explanation = area_data.get('explanation', '')
            
            confidence_score = {'high': 0.9, 'medium': 0.6, 'low': 0.3}.get(confidence, 0.6)
            
            insight = Insight(
                id=f"knowledge_area_{hash(area) % 100000}",
                category='milestone',
                title=f"Life Focus Area: {area}",
                description=f"Your Apple Notes indicate significant focus on {area}. {explanation}",
                significance_score=confidence_score * 0.9,
                sources=[],
                detected_at=datetime.now().isoformat(),
                time_context={'analysis_phase': 'title_batch', 'confidence': confidence},
                entities=[area],
                actionable=False
            )
            insights.append(insight)
        
        # Generate insights for notable events
        for event_data in title_analysis.get('notable_events', []):
            event = event_data.get('event', 'Unknown Event')
            significance = event_data.get('significance', 'medium')
            explanation = event_data.get('explanation', '')
            
            significance_score = {'high': 0.9, 'medium': 0.6, 'low': 0.3}.get(significance, 0.6)
            
            insight = Insight(
                id=f"knowledge_event_{hash(event) % 100000}",
                category='milestone',
                title=f"Notable Event: {event}",
                description=f"Significant event detected from Apple Note titles: {event}. {explanation}",
                significance_score=significance_score * 1.0,
                sources=[],
                detected_at=datetime.now().isoformat(),
                time_context={'analysis_phase': 'title_batch', 'significance': significance},
                entities=[event],
                actionable=False
            )
            insights.append(insight)
        
        # Generate insights for knowledge domains
        for domain_data in title_analysis.get('knowledge_domains', []):
            domain = domain_data.get('domain', 'Unknown Domain')
            confidence = domain_data.get('confidence', 'medium')
            explanation = domain_data.get('explanation', '')
            
            confidence_score = {'high': 0.9, 'medium': 0.6, 'low': 0.3}.get(confidence, 0.6)
            
            insight = Insight(
                id=f"knowledge_domain_{hash(domain) % 100000}",
                category='interesting',
                title=f"Knowledge Domain: {domain}",
                description=f"Your Apple Notes indicate you're developing expertise in {domain}. {explanation}",
                significance_score=confidence_score * 0.7,
                sources=[],
                detected_at=datetime.now().isoformat(),
                time_context={'analysis_phase': 'title_batch', 'confidence': confidence},
                entities=[domain],
                actionable=False
            )
            insights.append(insight)
        
        return insights
    
    def _select_documents_for_deep_analysis(self, documents: List[Dict], title_analysis: Dict) -> List[Dict]:
        """Select Apple Notes for deep analysis based on title analysis results"""
        if not title_analysis:
            # Fallback to original document set if no title analysis
            return documents[:100]  # Limit to prevent excessive processing
        
        # Extract keywords and themes from title analysis
        keywords = set()
        
        # Add primary interests as keywords
        for interest_data in title_analysis.get('primary_interests', []):
            interest = interest_data.get('interest', '')
            # Split interest into individual words
            keywords.update(interest.lower().split())
        
        # Add life areas as keywords
        for area_data in title_analysis.get('life_areas', []):
            area = area_data.get('area', '')
            keywords.update(area.lower().split())
        
        # Add knowledge domains as keywords
        for domain_data in title_analysis.get('knowledge_domains', []):
            domain = domain_data.get('domain', '')
            keywords.update(domain.lower().split())
        
        # Score documents based on keyword relevance
        scored_docs = []
        for doc in documents:
            metadata = doc.get('metadata', {})
            title = metadata.get('title', '').lower()
            text = metadata.get('text', '').lower()
            
            # Calculate relevance score based on keyword matches
            keyword_matches = sum(1 for keyword in keywords if keyword in title or keyword in text)
            
            # Boost score for documents with high confidence events or interests
            boost = 0
            for event_data in title_analysis.get('notable_events', []):
                if event_data.get('significance') == 'high':
                    event_keywords = event_data.get('event', '').lower().split()
                    if any(kw in title or kw in text for kw in event_keywords):
                        boost += 2
            
            relevance_score = keyword_matches + boost
            
            scored_docs.append({
                'document': doc,
                'relevance_score': relevance_score
            })
        
        # Sort by relevance and return top documents
        scored_docs.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Return top documents for deep analysis, ensuring we have enough
        selected_docs = [item['document'] for item in scored_docs[:80]]
        
        print(f"[INSIGHTS] Selected {len(selected_docs)} Apple Notes for deep analysis based on title analysis")
        
        return selected_docs
    
    def _generate_urgent_insights(self, scored_docs: List[Dict]) -> List[Insight]:
        """Generate urgent insights from Apple Notes"""
        insights = []
        
        for item in scored_docs[:20]:  # Check top 20
            if item['sentiment']['urgent'] > 0:
                doc = item['document']
                metadata = doc.get('metadata', {})
                
                insight = Insight(
                    id=f"urgent_{hash(metadata.get('text', '')) % 100000}",
                    category='urgent',
                    title=f"Urgent: {metadata.get('note_name', 'Apple Note')}",
                    description=f"Contains urgent keywords. {metadata.get('text', '')[:100]}...",
                    significance_score=item['score'] * 1.2,
                    sources=[doc],
                    detected_at=datetime.now().isoformat(),
                    time_context={'created_date': metadata.get('created_date', '')},
                    entities=metadata.get('entity_ids', []),
                    actionable=True
                )
                insights.append(insight)
        
        return insights
    
    def _generate_llm_milestone_insights(self, llm_insights: List[Dict]) -> List[Insight]:
        """Generate milestone insights from LLM analysis"""
        insights = []
        
        # Create individual insights for each LLM-generated event
        for llm_insight in llm_insights:
            doc = llm_insight.get('source_document', {})
            metadata = doc.get('metadata', {})
            
            # Create specific title based on event type
            event_type = llm_insight.get('type', 'milestone')
            title = llm_insight.get('title', f"{event_type.replace('_', ' ').title()} Detected")
            description = llm_insight.get('description', 'Significant event detected in your personal data')
            
            insight = Insight(
                id=f"llm_individual_{hash(str(llm_insight) + str(datetime.now())) % 100000}",
                category=llm_insight.get('category', 'milestone'),
                title=title,
                description=description,
                significance_score=llm_insight.get('significance_score', 0.7) * 1.2,
                sources=[doc],
                detected_at=datetime.now().isoformat(),
                time_context={
                    'created_date': metadata.get('created_date', ''),
                    'llm_generated': True,
                    'event_type': event_type,
                    'group': llm_insight.get('group', 'things')
                },
                entities=metadata.get('entity_ids', []),
                actionable=False
            )
            insights.append(insight)
        
        return insights
    
    def _generate_milestone_insights(self, scored_docs: List[Dict]) -> List[Insight]:
        """Generate milestone insights from detected life events"""
        insights = []
        
        for item in scored_docs[:20]:
            events = item['events']
            milestone_events = [e for e in events if 'milestone' in e['type'] or 'career' in e['type']]
            
            if milestone_events:
                doc = item['document']
                metadata = doc.get('metadata', {})
                text = metadata.get('text', '')
                
                for event in milestone_events:
                    event_type = event['type'].replace('_', ' ').title()
                    
                    # Extract more detailed information from the text
                    detailed_description = self._extract_milestone_details(event['type'], text, metadata)
                    
                    # Create more specific title based on event type
                    specific_title = self._create_milestone_title(event['type'], text, metadata)
                    
                    insight = Insight(
                        id=f"milestone_{hash(event_type + text) % 100000}",
                        category='milestone',
                        title=specific_title,
                        description=detailed_description,
                        significance_score=item['score'] * 1.1,
                        sources=[doc],
                        detected_at=datetime.now().isoformat(),
                        time_context={'created_date': metadata.get('created_date', '')},
                        entities=metadata.get('entity_ids', []),
                        actionable=False
                    )
                    insights.append(insight)
        
        return insights
    
    def _extract_milestone_details(self, event_type: str, text: str, metadata: Dict) -> str:
        """Extract detailed description of milestone from text"""
        text_lower = text.lower()
        
        # Extract relevant sentences or phrases
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        relevant_sentences = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in self._get_keywords_for_event(event_type)):
                relevant_sentences.append(sentence)
        
        if relevant_sentences:
            # Use the most relevant sentence(s)
            return " ".join(relevant_sentences[:2])
        
        # Fallback to context extraction
        if event_type == 'career_promotion':
            return "Career advancement detected. This appears to be a promotion or role change that represents professional growth."
        elif event_type == 'career_new_job':
            return "New career opportunity detected. This marks the beginning of a new professional journey."
        elif event_type == 'career_job_loss':
            return "Career transition detected. This represents a significant change in employment status."
        elif event_type == 'relationship_milestone':
            return "Important relationship milestone detected. This marks a significant moment in personal relationships."
        elif event_type == 'milestone_celebration':
            return "Personal celebration detected. This marks an important personal achievement or anniversary."
        elif event_type == 'milestone_achievement':
            return "Significant achievement detected. This represents the accomplishment of an important goal."
        else:
            return f"Important {event_type.replace('_', ' ')} detected in your personal data."
    
    def _create_milestone_title(self, event_type: str, text: str, metadata: Dict) -> str:
        """Create a specific title for the milestone"""
        text_lower = text.lower()
        
        # Try to extract specific details for title
        if event_type == 'career_promotion':
            if 'promoted' in text_lower:
                return "Career Promotion Detected"
            elif 'raise' in text_lower or 'salary' in text_lower:
                return "Salary Increase Detected"
            elif 'new role' in text_lower or 'new position' in text_lower:
                return "New Role Detected"
            else:
                return "Career Advancement"
        
        elif event_type == 'career_new_job':
            if 'hired' in text_lower:
                return "New Job Offer Accepted"
            elif 'started' in text_lower and 'job' in text_lower:
                return "New Job Started"
            elif 'offer' in text_lower:
                return "Job Opportunity Detected"
            else:
                return "Career Change Detected"
        
        elif event_type == 'relationship_milestone':
            if 'married' in text_lower or 'wedding' in text_lower:
                return "Wedding/Marriage Milestone"
            elif 'engagement' in text_lower or 'fianc' in text_lower:
                return "Engagement Detected"
            else:
                return "Relationship Milestone"
        
        elif event_type == 'milestone_celebration':
            if 'birthday' in text_lower:
                return "Birthday Celebration"
            elif 'anniversary' in text_lower:
                return "Anniversary Detected"
            elif 'graduation' in text_lower or 'graduated' in text_lower:
                return "Graduation Achievement"
            else:
                return "Personal Celebration"
        
        elif event_type == 'milestone_achievement':
            if 'award' in text_lower:
                return "Award/Recognition Received"
            elif 'certificate' in text_lower:
                return "Certification Achievement"
            else:
                return "Personal Achievement"
        
        else:
            return f"{event_type.replace('_', ' ').title()} Detected"
    
    def _get_keywords_for_event(self, event_type: str) -> List[str]:
        """Get relevant keywords for extracting context about an event"""
        keyword_map = {
            'career_promotion': ['promoted', 'promotion', 'raise', 'salary', 'new role', 'position'],
            'career_new_job': ['hired', 'offer', 'accepted', 'joined', 'started', 'job'],
            'career_job_loss': ['fired', 'laid off', 'resigned', 'quit', 'left'],
            'relationship_milestone': ['married', 'wedding', 'engagement', 'fianc'],
            'milestone_celebration': ['birthday', 'anniversary', 'graduation'],
            'milestone_achievement': ['achievement', 'award', 'recognition', 'certificate'],
        }
        
        return keyword_map.get(event_type, [])
    
    def _generate_trending_insights(self, scored_docs: List[Dict]) -> List[Insight]:
        """Generate trending insights from temporal analysis"""
        insights = []
        
        # Extract all documents
        documents = [item['document'] for item in scored_docs]
        
        # Analyze frequency
        frequency_data = self.temporal_analyzer.analyze_frequency(documents)
        trends = self.temporal_analyzer.detect_trends(frequency_data)
        
        for trend in trends[:5]:
            # Find documents related to this trend
            related_docs = [
                item for item in scored_docs
                if trend in item['document'].get('metadata', {}).get('entity_ids', []) or
                   trend in item['document'].get('metadata', {}).get('topics', [])
            ]
            
            if related_docs:
                avg_score = sum(d['score'] for d in related_docs) / len(related_docs)
                
                insight = Insight(
                    id=f"trending_{hash(trend) % 100000}",
                    category='trending',
                    title=f"Trending: {trend.replace('_', ' ').title()}",
                    description=f"Appears in {len(related_docs)} recent documents",
                    significance_score=avg_score * 0.9,
                    sources=[d['document'] for d in related_docs[:3]],
                    detected_at=datetime.now().isoformat(),
                    time_context={'frequency': frequency_data.get('entities', {}).get(trend, 0)},
                    entities=[trend],
                    actionable=False
                )
                insights.append(insight)
        
        return insights
    
    def _generate_interesting_insights(self, scored_docs: List[Dict]) -> List[Insight]:
        """Generate interesting insights from high-scoring Apple Notes"""
        insights = []
        
        for item in scored_docs[20:60]:  # Check documents 20-60
            if item['score'] > 0.6:
                doc = item['document']
                metadata = doc.get('metadata', {})
                
                insight = Insight(
                    id=f"interesting_{hash(metadata.get('text', '')) % 100000}",
                    category='interesting',
                    title=f"Notable: {metadata.get('note_name', 'Apple Note')}",
                    description=metadata.get('text', '')[:150] + "...",
                    significance_score=item['score'] * 0.8,
                    sources=[doc],
                    detected_at=datetime.now().isoformat(),
                    time_context={'created_date': metadata.get('created_date', '')},
                    entities=metadata.get('entity_ids', []),
                    actionable=False
                )
                insights.append(insight)
        
        return insights

    def _generate_journaling_insights(self, journaling_recs: List[Dict]) -> List[Insight]:
        """Generate insights from journaling recommendations"""
        insights = []

        for rec in journaling_recs:
            prompt = rec.get('prompt', '')
            reasoning = rec.get('reasoning', '')
            category = rec.get('category', 'general')

            insight = Insight(
                id=f"journaling_{hash(prompt) % 100000}",
                category='journaling',
                title=f"Journaling Prompt: {category.replace('-', ' ').title()}",
                description=f"{prompt}\n\nWhy this matters: {reasoning}",
                significance_score=0.85,  # High value for personalized prompts
                sources=[],
                detected_at=datetime.now().isoformat(),
                time_context={'category': category, 'type': 'recommendation'},
                entities=[],
                actionable=True
            )
            insights.append(insight)

        return insights

    def _generate_self_discovery_insights(self, self_discovery: List[Dict]) -> List[Insight]:
        """Generate insights from self-discovery analysis"""
        insights = []

        for discovery in self_discovery:
            category = discovery.get('category', 'general')
            insight_text = discovery.get('insight', '')
            evidence = discovery.get('evidence', '')
            significance_score = discovery.get('significance_score', 0.6)

            insight = Insight(
                id=f"discovery_{hash(insight_text) % 100000}",
                category='self_discovery',
                title=f"Self-Discovery: {category.replace('-', ' ').title()}",
                description=f"{insight_text}\n\nEvidence from your notes: {evidence}",
                significance_score=significance_score * 1.1,  # Boost for self-discovery value
                sources=[],
                detected_at=datetime.now().isoformat(),
                time_context={'category': category, 'type': 'self_discovery'},
                entities=[],
                actionable=False
            )
            insights.append(insight)

        return insights


def analyze_documents_for_insights(documents: List[Dict], user_id: str) -> List[Dict]:
    """
    Convenience function to analyze Apple Notes and return insights as dictionaries.
    
    Args:
        documents: List of Apple Note dictionaries with metadata
        user_id: User identifier
    
    Returns:
        List of insight dictionaries
    """
    engine = InsightsEngine()
    insights = engine.generate_insights(documents, user_id)
    
    return [
        {
            'id': insight.id,
            'category': insight.category,
            'title': insight.title,
            'description': insight.description,
            'significance_score': insight.significance_score,
            'sources': insight.sources,
            'detected_at': insight.detected_at,
            'time_context': insight.time_context,
            'entities': insight.entities,
            'actionable': insight.actionable
        }
        for insight in insights
    ]
