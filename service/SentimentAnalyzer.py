
from datetime import datetime

import os
import json
import asyncio
from typing import Optional
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from config import GITHUB_TOKEN, GITHUB_ENDPOINT, GITHUB_MODEL
from dotenv import load_dotenv
load_dotenv()

# Initialize GitHub client
client = None
if GITHUB_TOKEN:
    try:
        client = ChatCompletionsClient(
            endpoint=GITHUB_ENDPOINT,
            credential=AzureKeyCredential(GITHUB_TOKEN)
        )
    except Exception as e:
        print(f"Warning: Could not initialize GitHub Models client: {e}")


class GitHubModelsSentimentAnalyzer:

    @staticmethod
    async def analyze_with_github(review: str, rating: int, review_id: Optional[str] = None, reviewer_name: str = "", review_at: datetime = datetime.now(), is_google: bool = False) -> dict:
        """Analyze using GitHub Models API"""
        start_time = datetime.now()

        prompt = f"""Analisis review pelanggan berikut secara mendalam:

            REVIEW: "{review}"
            RATING: {rating}/5

            Output JSON dengan format:
            {{
            "sentiment": "Positive" | "Neutral" | "Negative",
            "sentiment_score": <-1.0 to 1.0>,
            "themes": [<maksimal 5 tema spesifik>],
            "analysis_reasons": [<minimal 3 alasan detail>],
            "ai_suggestions": [<minimal 3 rekomendasi actionable>]
            }}

            ATURAN:
            1. Sentiment dari tone review (rating hanya referensi)
            2. Sentiment Score: Positive (0.3 to 1.0), Neutral (-0.3 to 0.3), Negative (-1.0 to -0.3)
            3. Themes: Kualitas Produk, Pelayanan, Harga, Kecepatan, Kebersihan, dll
            4. Analysis Reasons: Jelaskan detail kenapa sentiment tersebut
            5. AI Suggestions: Konkret dan actionable untuk business

            Output HANYA JSON valid, tanpa markdown atau teks tambahan."""

        try:
            if not client:
                raise Exception("GitHub Models client not initialized. Check GITHUB_TOKEN.")

            response = await asyncio.to_thread(
                client.complete,
                messages=[
                    {"role": "system", "content": "You are an expert sentiment analyzer for Indonesian customer reviews. Always output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                model=GITHUB_MODEL,
                temperature=1.0,
                top_p=1.0,
                max_tokens=1000,
            )

            content = response.choices[0].message.content.strip()

            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()

            result = json.loads(content)
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            return {
                "id": review_id,
                "review_text": review,
                "rating": rating,
                "reviewer_name": reviewer_name,
                "review_at": review_at,
                "sentiment": result["sentiment"],
                "sentiment_score": result["sentiment_score"],
                "themes": result["themes"],
                "analysis_reasons": result["analysis_reasons"],
                "ai_suggestions": result["ai_suggestions"],
                "processing_time_ms": round(processing_time, 2),
                "timestamp": datetime.now().isoformat(),
                "source": "github_models",
                "is_google": is_google
            }

        except Exception as e:
            print(f"GitHub Models API Error: {e}")
            return GitHubModelsSentimentAnalyzer.fallback_analysis(review, rating, review_id, str(e))

    @staticmethod
    def fallback_analysis(review: str, rating: int, review_id: Optional[str] = None, error_msg: str = "") -> dict:
        """Advanced rule-based fallback"""
        start_time = datetime.now()

        POSITIVE = {
            'strong': ['luar biasa', 'sangat bagus', 'excellent', 'perfect', 'terbaik', 'sempurna', 'istimewa'],
            'medium': ['bagus', 'baik', 'enak', 'puas', 'senang', 'recommended', 'mantap', 'ramah', 'cepat', 'bersih', 'nyaman'],
            'weak': ['lumayan', 'cukup', 'ok', 'oke']
        }

        NEGATIVE = {
            'strong': ['sangat buruk', 'terrible', 'parah banget', 'mengecewakan sekali', 'worst'],
            'medium': ['buruk', 'jelek', 'kecewa', 'lambat', 'lama', 'mahal', 'kotor', 'tidak enak', 'kurang', 'rusak'],
            'weak': ['tidak', 'kurang', 'biasa aja']
        }

        THEMES = {
            'Kualitas Produk': ['makanan', 'rasa', 'enak', 'menu', 'produk', 'lezat', 'fresh'],
            'Kualitas Pelayanan': ['pelayanan', 'service', 'ramah', 'staff', 'karyawan', 'sopan'],
            'Harga & Value': ['harga', 'mahal', 'murah', 'value', 'terjangkau'],
            'Kecepatan Layanan': ['cepat', 'lama', 'tunggu', 'antri', 'lambat'],
            'Kebersihan': ['bersih', 'kotor', 'higienis', 'rapi'],
            'Suasana': ['suasana', 'tempat', 'nyaman', 'lokasi', 'atmosfer']
        }

        text = review.lower()

        pos_score = (
            sum(2 for w in POSITIVE['strong'] if w in text) +
            sum(1 for w in POSITIVE['medium'] if w in text) +
            sum(0.3 for w in POSITIVE['weak'] if w in text)
        ) / 5
        pos_score = min(pos_score, 1.0)

        neg_score = (
            sum(2 for w in NEGATIVE['strong'] if w in text) +
            sum(1 for w in NEGATIVE['medium'] if w in text) +
            sum(0.3 for w in NEGATIVE['weak'] if w in text)
        ) / 5
        neg_score = min(neg_score, 1.0)

        text_score = (pos_score - neg_score) * 0.7
        rating_score = (rating - 3) / 2 * 0.3
        final_score = text_score + rating_score

        if final_score > 0.2:
            sentiment = "Positive"
        elif final_score < -0.2:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"

        themes = [theme for theme, keywords in THEMES.items() if any(kw in text for kw in keywords)]
        if not themes:
            themes = ['Pengalaman Umum']

        reasons = []
        if sentiment == "Positive":
            reasons.append(f"Review menunjukkan apresiasi tinggi (positif: {pos_score:.2f})")
            if rating >= 4:
                reasons.append(f"Rating {rating}/5 mengkonfirmasi kepuasan pelanggan")
            reasons.append("Tone keseluruhan positif dan merekomendasikan")
        elif sentiment == "Negative":
            reasons.append(f"Review mengandung keluhan signifikan (negatif: {neg_score:.2f})")
            if rating <= 2:
                reasons.append(f"Rating {rating}/5 menunjukkan ketidakpuasan serius")
            reasons.append("Customer mengekspresikan kekecewaan yang perlu ditindaklanjuti")
        else:
            reasons.append("Review menunjukkan pengalaman standar")
            reasons.append(f"Rating {rating}/5 berada di level netral")
            reasons.append(f"Balance antara positif ({pos_score:.2f}) dan negatif ({neg_score:.2f})")

        suggestions = []
        if sentiment == "Negative":
            suggestions.append("🚨 URGENT: Follow-up customer untuk resolve issue")
            if 'Kualitas Pelayanan' in themes:
                suggestions.append("📋 Training dan evaluasi ulang tim service")
            if 'Kecepatan Layanan' in themes:
                suggestions.append("⚡ Optimasi workflow untuk reduce waiting time")
            suggestions.append("💰 Tawarkan kompensasi untuk restore trust")
        elif sentiment == "Positive":
            suggestions.append("💌 Kirim thank you message untuk strengthen relationship")
            suggestions.append("📢 Jadikan testimoni untuk marketing")
            suggestions.append("⭐ Maintain excellent quality yang sudah diberikan")
        else:
            suggestions.append("📊 Monitor trend untuk identify improvement")
            suggestions.append("🎯 Proactive engagement untuk understand expectations")
            suggestions.append("💡 Follow-up survey untuk detailed feedback")

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "id": review_id,
            "review_text": review,
            "rating": rating,
            "sentiment": sentiment,
            "sentiment_score": round(max(-1.0, min(1.0, final_score)), 2),
            "themes": themes[:5],
            "analysis_reasons": reasons,
            "ai_suggestions": suggestions[:5],
            "processing_time_ms": round(processing_time, 2),
            "timestamp": datetime.now().isoformat(),
            "source": "rule_based_fallback",
            "note": f"Fallback used: {error_msg}" if error_msg else "Rule-based analysis"
        }