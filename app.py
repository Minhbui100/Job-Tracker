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
        cur.execute("""select company, position, location, st.status
                    from job join status_table st on job.status_id=st.id
                    order by company, position;""")
        jobs=cur.fetchall()
        job_list=[{"company":job[0], "position":job[1], "location":job[2], "status":job[3]} for job in jobs]
        cur.close()
        conn.close()
        return render_template("index.html", jobs=job_list)
    except Exception as e:
        print(f"Error fetching websites: {e}")
        return jsonify({"error": "Error fetching websites"}), 500
    
@app.route("/add", methods=["GET"])
def show_add_form():
    return render_template("add.html")

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
        "posting_link": request.form["posting_link"].lower(),
        "description": request.form["description"],
        "level": request.form["level"]
    }
    try:
        conn=get_db_connection()
        cur=conn.cursor()
        force = request.form.get("force") == "true"
        cur.execute("select * from job where company=%s and position=%s and location=%s;", (new_job["company"], new_job["position"], new_job["location"]))
        existing_job=cur.fetchone()
        if existing_job and not force:
            cur.close()
            conn.close()
            return jsonify({"duplicate": True, "message": f"Position {new_job['position']} at {new_job['company']} in {new_job['location']} already exists. Do you really want to add more?"}), 409
        cur.execute("""insert into job (company, position, location, status_id, salary, date_applied, note, posting_link, description, level) 
                    values (%s, %s, %s, (select id from status_table where status=%s), %s, %s, %s, %s, %s, (select id from level where name=%s))""",
                    (new_job["company"], new_job["position"], new_job["location"], new_job["status"], new_job["salary"], 
                     new_job["date_applied"], new_job["note"], new_job["posting_link"], new_job["description"], new_job["level"]))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        print(f"Error adding job: {e}")
        return jsonify({"error": "Error adding job"}), 500


@app.route("/job/<company>/<position>/<location>")
def get_job_details(company, position, location):
    try: 
        conn=get_db_connection()
        cur=conn.cursor()
        cur.execute("""SELECT 
            job.company,
            job.position,
            job.location,
            st.status,
            job.salary,
            job.date_applied,
            job.note,
            job.posting_link,
            job.description,
            lv.name
        FROM job
        JOIN status_table st 
            ON job.status_id = st.id
        JOIN level lv 
            ON job.level = lv.id
        WHERE job.company = %s
            AND job.position = %s
            AND job.location = %s;""", (company.lower(), position.lower(), location.lower()))
        jobs=cur.fetchall()
        if jobs:
            job_details=[{
                "company": job[0],
                "position": job[1],
                "location": job[2],
                "status": job[3],
                "salary": job[4],
                "date_applied": job[5].strftime("%Y-%m-%d"),
                "note": job[6],
                "posting_link": job[7],
                "description": job[8],
                "level": job[9]
            } for job in jobs]
            cur.close()
            conn.close()
            return render_template("job.html", job=job_details, company=company, position=position, location=location)
        else:
            cur.close()
            conn.close()
            return render_template("job.html", job=None)
    except Exception as e:
        print(f"Error fetching job details: {e}")
        return jsonify({"error": "Error fetching job details"}), 500
    




    
if __name__=="__main__":
    app.run(debug=True)