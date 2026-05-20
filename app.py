import re
import psycopg2
from flask import Flask, request, jsonify, render_template
from config import host, name, user, password

app=Flask(__name__)
def get_db_connection():
    return psycopg2.connect(
        host=host,
        database=name,
        user=user,
        password=password
    )

@app.route("/")
def get_alljobs():
    try:
        conn=get_db_connection()
        cur=conn.cursor()
        cur.execute("""select company, position, count(*) as application_count from job
                    group by company, position
                    order by company, position;""")
        jobs=cur.fetchall()
        job_list=[{"company":job[0], "position":job[1], "application_count":job[2]} for job in jobs]
        cur.close()
        conn.close()
        return render_template("index.html", jobs=job_list)
    except Exception as e:
        print(f"Error fetching websites: {e}")
        return jsonify({"error": "Error fetching websites"}), 500
    
@app.route("/add", methods=["POST"])
def add_job():
    new_job={
        "company": request.form["company"].lower(),
        "position": request.form["position"].lower(),
        "location": request.form["location"].lower(),
        "status": request.form["status"].lower(),
        "salary": re.sub(r"[^\d]", "", request.form["salary"]),
        "date_applied": request.form["date_applied"],
        "note": request.form["note"].lower(),
        "posting_link": request.form["posting_link"].lower()
    }
    try:
        conn=get_db_connection()
        cur=conn.cursor()
        force = request.form.get("force") == "true"
        cur.execute("select * from job where company=%s and position=%s;", (new_job["company"], new_job["position"]))
        existing_job=cur.fetchone()
        if existing_job and not force:
            cur.close()
            conn.close()
            return jsonify({"duplicate": True, "message": f"Position {new_job['position']} at {new_job['company']} already exists. Do you really want to add more?"}), 409
        cur.execute("""insert into job (company, position, location, status_id, salary, date_applied, note, posting_link) 
                    values (%s, %s, %s, (select id from status_table where status=%s), %s, %s, %s, %s)""",
                    (new_job["company"], new_job["position"], new_job["location"], new_job["status"], new_job["salary"], new_job["date_applied"], new_job["note"], new_job["posting_link"]))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        print(f"Error adding job: {e}")
        return jsonify({"error": "Error adding job"}), 500








    
if __name__=="__main__":
    app.run(debug=True)