import re
import os
import uuid
import psycopg2
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
from config import host, name, user, password

app=Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return filename.lower().endswith(".pdf")
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
        "salary": int(float(s)) if (s := re.sub(r"[^\d.]", "", request.form["salary"])) else None,
        "date_applied": request.form["date_applied"],
        "note": request.form["note"].lower(),
        "posting_link": request.form["posting_link"],
        "description": request.form["description"],
        "level": request.form["level"]
    }
    cv_path = None
    file = request.files.get("cv")
    if file and file.filename and allowed_file(file.filename):
        filename = f"{uuid.uuid4().hex}.pdf"
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        cv_path = filename
    try:
        conn=get_db_connection()
        cur=conn.cursor()
        cur.execute("""select * from job 
                    where company=%s and position=%s and location=%s;""", 
                    (new_job["company"], new_job["position"], new_job["location"]))
        existing_job=cur.fetchone()
        if existing_job:
            cur.close()
            conn.close()
            return jsonify({"duplicate": True, "message": f"You already have an application for {new_job['position']} at {new_job['company']} in {new_job['location']}.\n Can not add another."}), 409
        
        cur.execute("""insert into job (company, position, location, status_id, salary, date_applied, note, posting_link, description, level, cv_path)
                    values (%s, %s, %s, (select id from status_table where status=%s), %s, %s, %s, %s, %s, (select id from level where name=%s), %s)""",
                    (new_job["company"], new_job["position"], new_job["location"], new_job["status"], new_job["salary"],
                     new_job["date_applied"], new_job["note"], new_job["posting_link"], new_job["description"], new_job["level"], cv_path))
        
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
            lv.name,
            job.cv_path
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
                "level": job[9],
                "cv_path": job[10]
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
    
@app.route("/delete/<company>/<position>/<location>", methods=["POST"])
def delete_job(company, position, location):
    try:
        conn=get_db_connection()
        cur=conn.cursor()
        cur.execute("select cv_path from job where company=%s and position=%s and location=%s;",
                    (company.lower(), position.lower(), location.lower()))
        row=cur.fetchone()
        if row and row[0]:
            cv_file=os.path.join(UPLOAD_FOLDER, row[0])
            if os.path.exists(cv_file):
                os.remove(cv_file)
        cur.execute("delete from job where company=%s and position=%s and location =%s;",
                    (company.lower(), position.lower(), location.lower()))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("get_alljobs"))
    except Exception as e:
        conn.rollback()
        print(f"Error deleting job: {e}")
        return jsonify({"error": "Error deleting job"}), 500

@app.route("/edit/<company>/<position>/<location>", methods=["GET"])
def show_edit_form(company, position, location):
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
            lv.name,
            job.cv_path
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
                "level": job[9],
                "cv_path": job[10]
            } for job in jobs]
            cur.close()
            conn.close()
            return render_template("edit.html", job=job_details[0], company=company, position=position, location=location)
        else:
            cur.close()
            conn.close()
            return render_template("edit.html", job=None)
    except Exception as e:
        print(f"Error fetching job details: {e}")
        return jsonify({"error": "Error fetching job details"}), 500

@app.route("/edit/<company>/<position>/<location>", methods=["POST"])
def edit_job(company, position, location):
    update={
        "company": company.lower(),
        "position": position.lower(),
        "location": location.lower(),
        "status": request.form["status"].lower(),
        "salary": int(float(s)) if (s := re.sub(r"[^\d.]", "", request.form["salary"])) else None,
        "date_applied": request.form["date_applied"],
        "note": request.form["note"].lower(),
        "posting_link": request.form["posting_link"],
        "description": request.form["description"],
        "level": request.form["level"]
    }
    existing_cv = request.form.get("existing_cv") or None
    remove_cv = request.form.get("remove_cv") == "on"
    cv_path = existing_cv

    file = request.files.get("cv")
    if file and file.filename and allowed_file(file.filename):
        if existing_cv:
            old_file = os.path.join(UPLOAD_FOLDER, existing_cv)
            if os.path.exists(old_file):
                os.remove(old_file)
        filename = f"{uuid.uuid4().hex}.pdf"
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        cv_path = filename
    elif remove_cv:
        if existing_cv:
            old_file = os.path.join(UPLOAD_FOLDER, existing_cv)
            if os.path.exists(old_file):
                os.remove(old_file)
        cv_path = None

    try:
        conn=get_db_connection()
        cur=conn.cursor()
        cur.execute("""update job set company=%s, position=%s, location=%s, status_id=(select id from status_table where status=%s),
                    salary=%s, date_applied=%s, note=%s, posting_link=%s, description=%s, level=(select id from level where name=%s), cv_path=%s
                    where company=%s and position=%s and location=%s;""",
                    (update["company"], update["position"], update["location"], update["status"], update["salary"],
                     update["date_applied"], update["note"], update["posting_link"], update["description"], update["level"], cv_path,
                     company.lower(), position.lower(), location.lower()))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("get_job_details", company=update["company"], position=update["position"], location=update["location"]))
    except Exception as e:
        conn.rollback()
        print(f"Error updating job: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/cv/<filename>")
def serve_cv(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__=="__main__":
    app.run(debug=True)