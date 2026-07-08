import ast
import re

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

tree = ast.parse(text)
remove_ranges = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in ('save_portfolio', 'get_my_portfolios', 'delete_portfolio', 'view_portfolio'):
        start = node.lineno
        if node.decorator_list:
            start = min(d.lineno for d in node.decorator_list)
        remove_ranges.append((start, node.end_lineno))

lines = text.split('\n')
remove_set = set()
for s, e in remove_ranges:
    for i in range(s, e + 1):
        remove_set.add(i)

new_lines = [line for i, line in enumerate(lines, 1) if i not in remove_set]

new_endpoints = """
@app.route("/api/portfolio", methods=["POST"])
def save_portfolio_api():
    try:
        data = request.json
        import json
        
        portfolio = SavedPortfolio(
            name=data["name"],
            csv_content=data["csv_content"],
            start_date=data["start_date"],
            benchmark_ticker=data["benchmark_ticker"],
            base_currency=data["base_currency"],
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        full_data = {
            "csv_content": data["csv_content"],
            "metrics": data.get("metrics", {}),
            "summary": data.get("summary", {}),
            "holdings_table": data.get("holdings_table", ""),
            "allocation_data": data.get("allocation_data", {}),
            "chart_data": data.get("chart_data", {}),
        }
        portfolio.csv_content = json.dumps(full_data, ensure_ascii=False)
        db.session.add(portfolio)
        db.session.commit()
        return jsonify({"success": True, "message": "Saved successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/api/portfolio", methods=["GET"])
def get_portfolios_api():
    try:
        portfolios = SavedPortfolio.query.order_by(SavedPortfolio.created_at.desc()).all()
        result = []
        import json
        for p in portfolios:
            try:
                data = json.loads(p.csv_content)
                result.append({
                    "id": p.id,
                    "name": p.name,
                    "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
                    "csv_content": data.get("csv_content", "")
                })
            except:
                continue
        return jsonify({"success": True, "portfolios": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/portfolio/<int:pid>", methods=["DELETE"])
def delete_portfolio_api(pid):
    try:
        portfolio = SavedPortfolio.query.get(pid)
        if portfolio:
            db.session.delete(portfolio)
            db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
"""

out_lines = []
for line in new_lines:
    if line.strip().startswith('if __name__ == "__main__":'):
        out_lines.append(new_endpoints)
    out_lines.append(line)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_lines))
