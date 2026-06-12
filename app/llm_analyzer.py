"""
LLM-based analysis of documents for insights
"""

import os
import json
import re
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage


class LLMInsightAnalyzer:
    """Uses LLM to analyze flagged documents for meaningful insights"""
    
    def __init__(self):
        # Initialize LLM if available
        self.llm = None
        try:
            self.llm = ChatOpenAI(
                model="openai/gpt-oss-20b:free",
                temperature=0.2,
                openai_api_key=os.getenv("OPEN_ROUTER_API_KEY"),
                openai_api_base="https://openrouter.ai/api/v1"
            )
        except Exception as e:
            print(f"Warning: Could not initialize LLM for insight analysis: {e}")
    
    def analyze_flagged_documents(self, documents: List[Dict]) -> List[Dict]:
        """Analyze flagged documents using LLM to extract meaningful insights"""
        if not self.llm:
            return []
        
        # Limit to 20 documents for more comprehensive analysis
        max_docs = 20
        if len(documents) > max_docs:
            print(f"[INSIGHTS] Limiting analysis to {max_docs} documents (was {len(documents)})")
            documents = documents[:max_docs]
        
        print(f"[INSIGHTS] Starting analysis of {len(documents)} flagged documents")
        insights = []
        
        def analyze_single_document_sync(doc):
            """Synchronously analyze a single document"""
            print(f"[INSIGHTS] Analyzing document: {doc.get('id', 'unknown')}")
            metadata = doc.get('metadata', {})
            text = metadata.get('text', '')
            source = metadata.get('source', 'unknown')
            
            if len(text) < 50:  # Skip very short documents
                print(f"[INSIGHTS] Skipping short document: {len(text)} chars")
                return []
            
            try:
                print(f"[INSIGHTS] Creating analysis prompt for document...")
                # Create analysis prompt
                prompt = self._create_analysis_prompt(text, source, metadata)
                message = HumanMessage(content=prompt)
                
                print(f"[INSIGHTS] Invoking LLM for document...")
                response = self.llm.invoke([message])
                print(f"[INSIGHTS] LLM response received for document")
                
                analysis = response.content.strip()
                print(f"[INSIGHTS] Raw LLM response (first 500 chars): {analysis[:500]}")
                
                print(f"[INSIGHTS] Parsing LLM response...")
                # Parse LLM response
                result = self._parse_llm_response(analysis, doc)
                print(f"[INSIGHTS] Document analysis complete: {len(result)} insights")
                return result
                
            except Exception as e:
                print(f"[INSIGHTS] Error analyzing document with LLM: {e}")
                import traceback
                traceback.print_exc()
                return []
        
        # Process documents sequentially
        print(f"[INSIGHTS] Starting sequential processing...")
        
        for i, doc in enumerate(documents):
            print(f"[INSIGHTS] Processing document {i+1}/{len(documents)}")
            try:
                doc_insights = analyze_single_document_sync(doc)
                insights.extend(doc_insights)
                print(f"[INSIGHTS] Document {i+1} completed, total insights so far: {len(insights)}")
            except Exception as e:
                print(f"[INSIGHTS] Error processing document {i+1}: {e}")
                continue
        
        print(f"[INSIGHTS] Analysis complete: {len(insights)} insights generated")
        return insights
    
    def _create_analysis_prompt(self, text: str, source: str, metadata: Dict) -> str:
        """Create a prompt for LLM analysis of a document"""
        created_date = metadata.get('created_date', 'unknown')
        
        prompt = f"""Analyze this personal document for important life events, milestones, or significant insights. 

Document Source: {source}
Date: {created_date}
Content: {text[:1000]}...

Please identify and categorize any significant life events, milestones, or insights in this document. Focus on events that are NOT necessarily about the user directly, but about people, places, or things in their life.

Categorize events into:
1. People (relationships, family events, social gatherings, friend activities)
2. Places (location changes, travel, moves, venue events)
3. Things (projects, achievements, purchases, objects, events)

For each significant event found, provide:
- Event type (category)
- Group (people/places/things)
- Brief title (1-2 sentences)
- Detailed description (2-3 sentences)
- Significance level (low/medium/high)

Format your response as JSON:
{{
  "insights": [
    {{
      "category": "milestone",
      "type": "relationship_milestone",
      "group": "people",
      "title": "Social Event Detected",
      "description": "A social gathering or relationship event was identified in the document.",
      "significance": "medium"
    }}
  ]
}}

If no significant events are found, return {{"insights": []}}."""
        
        return prompt
    
    def _parse_llm_response(self, response: str, doc: Dict) -> List[Dict]:
        """Parse LLM response to extract insights"""
        try:
            # First, try to extract JSON from markdown code blocks
            json_content = response
            if '```' in response:
                # Try to extract JSON from markdown code blocks
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                    print(f"[INSIGHTS] Extracted JSON from markdown code block")
                else:
                    # Fallback to any JSON-like structure
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        json_content = json_match.group(0)
                        print(f"[INSIGHTS] Extracted JSON using regex fallback")
            
            # Try to parse as JSON
            parsed = json.loads(json_content)
            
            if 'insights' not in parsed:
                print(f"[INSIGHTS] No 'insights' key found in LLM response")
                return []
            
            insights = []
            for insight_data in parsed['insights']:
                # Convert significance to score
                significance_map = {'low': 0.3, 'medium': 0.6, 'high': 0.9}
                significance_score = significance_map.get(insight_data.get('significance', 'medium'), 0.6)
                
                insight = {
                    'type': insight_data.get('type', 'unknown'),
                    'category': insight_data.get('category', 'milestone'),
                    'group': insight_data.get('group', 'things'),  # Add group categorization
                    'title': insight_data.get('title', 'Life Event Detected'),
                    'description': insight_data.get('description', 'Significant event detected in personal data'),
                    'significance_score': significance_score,
                    'source_document': doc,
                    'llm_generated': True
                }
                insights.append(insight)
            
            print(f"[INSIGHTS] Successfully parsed {len(insights)} insights from LLM response")
            return insights
            
        except json.JSONDecodeError as e:
            print(f"[INSIGHTS] JSON decode error: {e}")
            # Fallback: try to extract insights from plain text
            return self._parse_text_response(response, doc)
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return []
    
    def _parse_text_response(self, response: str, doc: Dict) -> List[Dict]:
        """Fallback parser for non-JSON responses"""
        insights = []
        
        # Simple keyword-based extraction from text response
        lines = response.split('\n')
        current_insight = {}
        
        for line in lines:
            line = line.strip()
            if 'category:' in line.lower():
                if current_insight:
                    insights.append(current_insight)
                current_insight = {'category': line.split(':', 1)[1].strip()}
            elif 'title:' in line.lower():
                current_insight['title'] = line.split(':', 1)[1].strip()
            elif 'description:' in line.lower():
                current_insight['description'] = line.split(':', 1)[1].strip()
            elif 'significance:' in line.lower():
                sig = line.split(':', 1)[1].strip().lower()
                significance_map = {'low': 0.3, 'medium': 0.6, 'high': 0.9}
                current_insight['significance_score'] = significance_map.get(sig, 0.6)
        
        if current_insight:
            current_insight['source_document'] = doc
            current_insight['llm_generated'] = True
            insights.append(current_insight)
        
        return insights
    
    def analyze_document_titles_batch(self, documents: List[Dict]) -> Dict:
        """Analyze document titles in batches to identify interests and basic information"""
        if not self.llm:
            return {}
        
        # Extract titles and basic metadata
        titles_data = []
        for doc in documents:
            metadata = doc.get('metadata', {})
            source = metadata.get('source', 'unknown')
            created_date = metadata.get('created_date', '')
            
            # Get title - handle different source types
            title = ''
            if source == 'apple_notes':
                title = metadata.get('note_name', '')
            elif source == 'gmail':
                title = metadata.get('subject', '')
            else:
                title = metadata.get('title', '')
            
            print(f"[INSIGHTS] Doc {doc.get('id', 'unknown')}: source={source}")
            print(f"[INSIGHTS] Metadata keys: {list(metadata.keys())}")
            print(f"[INSIGHTS] Subject field: {metadata.get('subject', 'NOT_FOUND')}")
            print(f"[INSIGHTS] Title field: {metadata.get('title', 'NOT_FOUND')}")
            print(f"[INSIGHTS] Extracted title: '{title}', len={len(title.strip()) if title else 0}")
            
            if title and len(title.strip()) > 0:
                titles_data.append({
                    'title': title,
                    'source': source,
                    'date': created_date,
                    'doc_id': doc.get('id', 'unknown')
                })
        
        print(f"[INSIGHTS] Total valid titles found: {len(titles_data)}")
        if not titles_data:
            print("[INSIGHTS] No valid titles found for batch analysis")
            return {}
        
        # Limit to 5 documents for faster processing
        titles_data = titles_data[:5]
        
        # Create batch of titles for analysis
        titles_text = "\n".join([f"- [{item['source']}] {item['title']}" for item in titles_data])
        
        print(f"[INSIGHTS] Starting batch title analysis of {len(titles_data)} documents")
        
        try:
            # Create analysis prompt for titles
            prompt = f"""Analyze these document titles to identify the user's main interests, activities, and life patterns.

Document Titles:
{titles_text}

Please analyze and categorize the information into:
1. **Primary Interests**: Main topics/themes the user engages with
2. **Life Areas**: Key areas of focus (career, relationships, health, finance, etc.)
3. **Activity Patterns**: Types of activities and their frequency
4. **Notable Events**: Significant events or milestones indicated by titles
5. **Knowledge Domains**: Areas where the user has expertise or is learning

For each category, provide:
- The identified items
- Confidence level (high/medium/low)
- Brief explanation

Format your response as JSON:
{{
  "primary_interests": [
    {{"interest": "topic", "confidence": "high", "explanation": "why this was identified"}}
  ],
  "life_areas": [
    {{"area": "category", "confidence": "medium", "explanation": "evidence from titles"}}
  ],
  "activity_patterns": [
    {{"pattern": "activity type", "frequency": "high/medium/low", "explanation": "observation"}}
  ],
  "notable_events": [
    {{"event": "event description", "significance": "high/medium/low", "explanation": "context"}}
  ],
  "knowledge_domains": [
    {{"domain": "area of knowledge", "confidence": "high", "explanation": "learning indicators"}}
  ]
}}

Focus on patterns and themes rather than individual documents. Be comprehensive but concise."""
            
            message = HumanMessage(content=prompt)
            
            try:
                response = self.llm.invoke([message])
                print("[INSIGHTS] Batch title analysis completed")
                analysis = response.content.strip()
            except Exception as e:
                print(f"[INSIGHTS] Error in batch title analysis LLM call: {e}")
                return {}
            
            # Debug: print the raw response
            print(f"[INSIGHTS] Raw LLM response (first 500 chars): {analysis[:500]}")
            
            # Parse the response - try multiple approaches
            try:
                parsed = json.loads(analysis)
                print(f"[INSIGHTS] Successfully parsed batch analysis: {len(parsed)} categories")
                return parsed
            except json.JSONDecodeError as e:
                print(f"[INSIGHTS] JSON decode error: {e}")
                
                # Try to extract JSON from markdown code blocks or plain text
                try:
                    # First try to extract from markdown code blocks
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', analysis, re.DOTALL)
                    if not json_match:
                        # Fallback to any JSON-like structure
                        json_match = re.search(r'\{.*\}', analysis, re.DOTALL)
                    
                    if json_match:
                        json_str = json_match.group(1) if json_match.lastindex == 1 else json_match.group(0)
                        parsed = json.loads(json_str)
                        print(f"[INSIGHTS] Successfully extracted JSON with regex: {len(parsed)} categories")
                        return parsed
                except Exception as e2:
                    print(f"[INSIGHTS] Regex extraction failed: {e2}")
                
                print("[INSIGHTS] Failed to parse batch analysis as JSON")
                print(f"[INSIGHTS] Full response: {analysis}")
                return {}
            
        except Exception as e:
            print(f"[INSIGHTS] Error in batch title analysis: {e}")
            return {}

    def generate_journaling_recommendations(self, documents: List[Dict]) -> List[Dict]:
        """Generate personalized journaling recommendations based on user's notes"""
        if not self.llm:
            return []

        # Extract recent notes and themes
        recent_notes = []
        for doc in documents[:20]:  # Focus on recent 20 notes
            metadata = doc.get('metadata', {})
            text = metadata.get('text', '')
            title = metadata.get('note_name', '')
            created_date = metadata.get('created_date', '')

            if text and len(text) > 50:
                recent_notes.append({
                    'title': title,
                    'text': text[:500],  # Truncate for context
                    'date': created_date
                })

        if not recent_notes:
            return []

        # Create context from recent notes
        notes_context = "\n\n".join([
            f"Title: {note['title']}\nDate: {note['date']}\nContent: {note['text']}"
            for note in recent_notes[:10]
        ])

        try:
            prompt = f"""Based on these recent Apple Notes, generate 3-5 personalized journaling recommendations for the user.

Recent Notes:
{notes_context}

Analyze the notes to identify:
1. Topics the user has mentioned but hasn't explored deeply
2. Goals or intentions the user has expressed
3. Recurring themes or patterns in their writing
4. Areas where the user seems to be seeking clarity
5. Experiences or emotions that could benefit from deeper reflection

For each recommendation, provide:
- A specific journaling prompt or question
- Why this recommendation is relevant to them (based on their notes)
- The category (goal-reflection, pattern-exploration, emotion-processing, clarity-seeking, future-planning)

Format your response as JSON:
{{
  "recommendations": [
    {{
      "prompt": "Specific journaling question or prompt",
      "reasoning": "Why this is relevant based on their notes",
      "category": "goal-reflection"
    }}
  ]
}}

Make the prompts personal and specific to what you've learned about them from their notes."""

            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])
            analysis = response.content.strip()

            # Parse response
            try:
                # Try to extract JSON from markdown code blocks
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', analysis, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                else:
                    json_match = re.search(r'\{.*\}', analysis, re.DOTALL)
                    if json_match:
                        json_content = json_match.group(0)
                    else:
                        return []

                parsed = json.loads(json_content)

                if 'recommendations' not in parsed:
                    return []

                recommendations = []
                for rec in parsed['recommendations']:
                    recommendations.append({
                        'prompt': rec.get('prompt', ''),
                        'reasoning': rec.get('reasoning', ''),
                        'category': rec.get('category', 'general')
                    })

                return recommendations

            except json.JSONDecodeError as e:
                print(f"[INSIGHTS] JSON decode error in journaling recommendations: {e}")
                return []

        except Exception as e:
            print(f"[INSIGHTS] Error generating journaling recommendations: {e}")
            return []

    def generate_self_discovery_insights(self, documents: List[Dict]) -> List[Dict]:
        """Generate deep self-discovery insights about the user"""
        if not self.llm:
            return []

        # Extract notes for analysis
        notes_for_analysis = []
        for doc in documents[:30]:  # Analyze up to 30 notes
            metadata = doc.get('metadata', {})
            text = metadata.get('text', '')
            title = metadata.get('note_name', '')
            created_date = metadata.get('created_date', '')

            if text and len(text) > 50:
                notes_for_analysis.append({
                    'title': title,
                    'text': text[:800],  # More context for self-discovery
                    'date': created_date
                })

        if not notes_for_analysis:
            return []

        # Create context
        notes_context = "\n\n".join([
            f"Title: {note['title']}\nDate: {note['date']}\nContent: {note['text']}"
            for note in notes_for_analysis[:15]
        ])

        try:
            prompt = f"""Analyze these Apple Notes to generate deep self-discovery insights about the user.

Notes:
{notes_context}

Look for patterns and insights about:
1. **Core Values**: What principles or beliefs seem important to them?
2. **Joy Sources**: What consistently brings them happiness or fulfillment?
3. **Stress Triggers**: What situations or topics seem to cause stress or anxiety?
4. **Recurring Conflicts**: What internal conflicts or dilemmas appear repeatedly?
5. **Growth Areas**: Where are they actively trying to improve or learn?
6. **Relationship Patterns**: How do they describe their interactions with others?
7. **Decision-Making**: How do they approach important choices?

For each insight, provide:
- The insight category (values, joy-sources, stress-triggers, recurring-conflicts, growth-areas, relationship-patterns, decision-making)
- A clear, specific insight about them
- Evidence from their notes that supports this insight
- Significance level (low/medium/high)

Format your response as JSON:
{{
  "insights": [
    {{
      "category": "values",
      "insight": "Specific insight about their values",
      "evidence": "Quote or pattern from their notes",
      "significance": "high"
    }}
  ]
}}

Be specific and personal. Use their actual words when possible. Focus on insights that would help them understand themselves better."""

            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])
            analysis = response.content.strip()

            # Parse response
            try:
                # Try to extract JSON from markdown code blocks
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', analysis, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                else:
                    json_match = re.search(r'\{.*\}', analysis, re.DOTALL)
                    if json_match:
                        json_content = json_match.group(0)
                    else:
                        return []

                parsed = json.loads(json_content)

                if 'insights' not in parsed:
                    return []

                insights = []
                for insight_data in parsed['insights']:
                    significance_map = {'low': 0.3, 'medium': 0.6, 'high': 0.9}
                    significance_score = significance_map.get(insight_data.get('significance', 'medium'), 0.6)

                    insights.append({
                        'category': insight_data.get('category', 'general'),
                        'insight': insight_data.get('insight', ''),
                        'evidence': insight_data.get('evidence', ''),
                        'significance_score': significance_score
                    })

                return insights

            except json.JSONDecodeError as e:
                print(f"[INSIGHTS] JSON decode error in self-discovery insights: {e}")
                return []

        except Exception as e:
            print(f"[INSIGHTS] Error generating self-discovery insights: {e}")
            return []
