from ploidy import dashboard


def test_render_debate_list_escapes_prompt_and_id():
    html = dashboard._render_debate_list(
        [
            {
                "id": 'abc"><script>alert(1)</script>',
                "prompt": "<img src=x onerror=alert(1)>",
                "status": "active",
                "created_at": "2026-03-19",
            }
        ]
    )

    assert "<script>alert(1)</script>" not in html
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html


def test_render_debate_detail_escapes_transcript_and_synthesis():
    html = dashboard._render_debate_detail(
        {
            "id": "d1",
            "prompt": "<b>prompt</b>",
            "status": "complete",
            "created_at": "2026-03-19",
            "sessions": [{"id": "s1", "role": "experienced"}],
            "messages": [
                {
                    "session_id": "s1",
                    "phase": "position",
                    "content": '<script>alert("x")</script>',
                    "action": 'challenge" onclick="alert(1)',
                    "timestamp": "2026-03-19T00:00:00Z",
                }
            ],
            "convergence": {
                "confidence": 0.5,
                "points_json": '[{"category":"agreement","summary":"<svg onload=alert(1)>"}]',
                "synthesis": "<iframe></iframe>",
                "created_at": "2026-03-19",
            },
        }
    )

    assert '<script>alert("x")</script>' not in html
    assert "<iframe></iframe>" not in html
    assert "<svg onload=alert(1)>" not in html
    assert "&lt;b&gt;prompt&lt;/b&gt;" in html
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in html
    assert "&lt;iframe&gt;&lt;/iframe&gt;" in html
