#!/usr/bin/env python3
"""MCP server for persian-geo-analyzer (stdlib only, stdio transport).

Exposes one tool:

  analyze_fa_geo — score Persian text (or a fetched URL) for AI citability
    params: { "text": str } | { "url": str }
    returns: total_score, grade, Persian label, per-category breakdown,
             word count and Persian fix suggestions.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fa_geo import analyze_blocks, analyze_text, analyze_url, extract_blocks  # noqa: E402


def _result(content):
    return {"content": [{"type": "text", "text": content}]}


def handle(request):
    method = request.get("method")
    rid = request.get("id")

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid,
                "result": {"protocolVersion": "2024-11-05",
                           "capabilities": {"tools": {}},
                           "serverInfo": {"name": "persian-geo-analyzer",
                                          "version": "1.0.0"}}}
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid,
                "result": {"tools": [{
                    "name": "analyze_fa_geo",
                    "description": (
                        "Analyze Persian (Farsi) content for AI-search citability "
                        "(GEO). Scores 0-100 across 5 categories with Persian fix "
                        "suggestions. Give it raw text or a URL."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string",
                                     "description": "Persian text to analyze"},
                            "url": {"type": "string",
                                    "description": "Page URL to fetch and analyze"},
                            "heading": {"type": "string",
                                        "description": "Optional heading/title of the text"},
                        },
                    }}]}}
    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {}) or {}
        if name != "analyze_fa_geo":
            return {"jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32602, "message": f"unknown tool: {name}"}}
        try:
            if args.get("url"):
                report = analyze_url(args["url"])
                summary = (f"بلوک‌ها: {report['total_blocks']} — "
                           f"میانگین نمره: {report['average_score']}/100")
                top = report["top_blocks"][0] if report["top_blocks"] else None
                detail = ""
                if top:
                    detail = (f"\nبهترین بلوک: {top['total_score']}/100 "
                              f"(درجه {top['grade']}) — {top['heading']}"
                              f"\nپیشنهادها: {'; '.join(top['fixes'])}")
                return {"jsonrpc": "2.0", "id": rid,
                        "result": _result(summary + detail +
                                          "\n\n```json\n" +
                                          json.dumps(report, ensure_ascii=False,
                                                     default=str)[:6000] +
                                          "\n```")}
            text = args.get("text", "")
            if not text.strip():
                return {"jsonrpc": "2.0", "id": rid,
                        "error": {"code": -32602,
                                  "message": "provide 'text' or 'url'"}}
            if "<" in text and ">" in text:
                report = analyze_blocks(extract_blocks(text))
            else:
                report = analyze_text(text, args.get("heading"))
            return {"jsonrpc": "2.0", "id": rid,
                    "result": _result(json.dumps(report, ensure_ascii=False,
                                                 indent=2, default=str))}
        except Exception as e:  # noqa: BLE001 — report tool errors over MCP
            return {"jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32603, "message": str(e)}}
    return {"jsonrpc": "2.0", "id": rid,
            "error": {"code": -32601, "message": f"unknown method: {method}"}}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            response = handle(json.loads(line))
        except Exception as e:  # noqa: BLE001
            response = {"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32700, "message": str(e)}}
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
