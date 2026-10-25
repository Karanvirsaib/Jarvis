import json
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from core import job_search


class ResumeProfileTests(unittest.TestCase):
    def test_profile_extraction_is_local_and_limits_output_to_matching_facts(self):
        payload = {
            'ok': True, 'page_count': 1, 'pages_with_text': 1,
            'text': ('Karanvir Singh\nSenior Data Analyst | Power BI | SQL | Tableau | Python\n'
                     'Noida, NCR, India | karan@example.com\n'
                     'Senior Data Analyst with 4+ years experience. Seeking Senior Data Analyst / BI Analyst / Power BI Engineer roles where SQL drives impact.\n'
                     'Education: Bachelor of Technology (B.Tech), Mechanical Engineering | 2019\n'
                     'Skills: Power BI, SQL, Tableau, Python, Azure Data Factory, Databricks'),
        }
        process = Mock(returncode=0, stdout=json.dumps(payload), stderr='')
        with patch.object(job_search.subprocess, 'run', return_value=process) as run:
            profile = job_search.extract_resume_profile('selected.pdf', 'python.exe', 'extract.py')
        run.assert_called_once()
        self.assertEqual(profile['roles'], ['Senior Data Analyst', 'BI Analyst', 'Power BI Engineer'])
        self.assertEqual(profile['years_experience'], 4.0)
        self.assertEqual(profile['location'], 'Noida, NCR, India')
        self.assertNotIn('karan@example.com', json.dumps(profile['skills']))
        self.assertIn('Azure Data Factory', profile['skills'])
        self.assertIn('Mechanical Engineering', profile['education'])
        self.assertEqual(profile['work_arrangement_preference'], '')


class JobMatchingTests(unittest.TestCase):
    def test_single_matched_skill_cannot_fill_the_full_skill_score(self):
        profile = {'roles': ['Senior Data Analyst'], 'years_experience': 4.0, 'skills': ['SQL']}
        score, reasons, _concerns, _skills = job_search._score(
            profile, 'AI Data Analyst', 'AI Data Analyst. SQL.', 'India', '3-5 years',
        )
        self.assertEqual(score, 56)
        self.assertIn('Skill overlap: 9/45; shared skills: SQL.', reasons)

    def test_greenhouse_ats_page_uses_employer_name_from_apply_heading(self):
        page = {
            'url': 'https://job-boards.greenhouse.io/gleanwork/jobs/4739203005',
            'final_url': 'https://job-boards.greenhouse.io/gleanwork/jobs/4739203005',
            'employer_detail_verified': True,
        }
        self.assertEqual(
            job_search._company_from(page, {}, 'AI Data Analyst',
                                     'Job Application for AI Data Analyst at Glean Back to jobs'),
            'Glean',
        )

    def test_ats_company_slug_is_used_instead_of_ats_brand(self):
        greenhouse = {'url': 'https://job-boards.greenhouse.io/sigmoid/jobs/5481479002',
                      'final_url': 'https://job-boards.greenhouse.io/sigmoid/jobs/5481479002',
                      'employer_detail_verified': True}
        ashby = {'url': 'https://jobs.ashbyhq.com/cube/21ca82ff-ac98-4e88-b1c7-2aadac890732',
                 'final_url': 'https://jobs.ashbyhq.com/cube/21ca82ff-ac98-4e88-b1c7-2aadac890732',
                 'employer_detail_verified': True}
        noisy_schema = {'hiringOrganization': {'name': '** Sigmoid - **Location:** Bengaluru'}}
        self.assertEqual(job_search._company_from(greenhouse, noisy_schema, 'Senior Data Analyst', ''), 'Sigmoid')
        self.assertEqual(job_search._company_from(ashby, {}, 'Senior Data Analyst', ''), 'Cube')

    def test_employer_url_role_must_agree_with_search_title(self):
        accountant = {'url': 'https://example.wd5.myworkdayjobs.com/jobs/Accountant_NX-4454'}
        analyst = {'url': 'https://example.wd5.myworkdayjobs.com/jobs/Senior-Data-Analyst_R1234'}
        self.assertTrue(job_search._url_title_conflict(accountant, 'Senior BI Analyst'))
        self.assertFalse(job_search._url_title_conflict(analyst, 'Senior BI Analyst'))

    def test_gurugram_is_treated_as_ncr_for_location_fit(self):
        profile = {'roles': ['Senior Data Analyst'], 'years_experience': 4.0, 'skills': ['SQL', 'Power BI']}
        _score, reasons, concerns, _skills = job_search._score(
            profile, 'Senior Data Analyst', 'SQL Power BI Tableau Python Excel', 'Gurugram, IN', '4+ years',
        )
        self.assertIn('Location fit: 10/10 for Gurugram, IN.', reasons)
        self.assertFalse(any('Location or work mode' in item for item in concerns))

    def test_messy_location_summary_prefers_city_and_foreign_jobs_are_excluded(self):
        profile = {'roles': ['Senior Data Analyst'], 'years_experience': 4.0,
                   'location': 'Noida, NCR, India', 'skills': ['SQL', 'Power BI']}
        now = datetime.fromisoformat('2026-10-25T14:00:00+05:30')
        pages = [{
            'url': 'https://jobs.ashbyhq.com/g2/9a3fd4d0-7696-4e56-b75f-6c78a4b3d395',
            'final_url': 'https://jobs.ashbyhq.com/g2/9a3fd4d0-7696-4e56-b75f-6c78a4b3d395',
            'title': 'Senior Data Analyst', 'page_title': 'Senior Data Analyst',
            'snippet': 'Senior Data Analyst. Bengaluru - Type: FullTime - Team: Product R&D - Apply',
            'content': 'Senior Data Analyst. Bengaluru - Type: FullTime - Team: Product R&D - Apply. SQL Power BI Python.',
            'http_status': 200, 'employer_detail_verified': True, 'posting_available': True,
            'apply_links': [{'text': 'Apply', 'url': 'https://jobs.ashbyhq.com/g2/9a3fd4d0-7696-4e56-b75f-6c78a4b3d395/application'}],
            'structured_job': {'hiringOrganization': {'name': 'G2'}},
        }, {
            'url': 'https://jobs.ashbyhq.com/handshake/11625d7a-36cc-48b9-808a-ae020c0bf535',
            'final_url': 'https://jobs.ashbyhq.com/handshake/11625d7a-36cc-48b9-808a-ae020c0bf535',
            'title': 'Senior Data Analyst', 'page_title': 'Senior Data Analyst',
            'snippet': 'Senior Data Analyst. San Francisco, California, United States. Apply',
            'content': 'Senior Data Analyst. San Francisco, California, United States. Apply. SQL Power BI Python.',
            'http_status': 200, 'employer_detail_verified': True, 'posting_available': True,
            'apply_links': [{'text': 'Apply', 'url': 'https://jobs.ashbyhq.com/handshake/11625d7a-36cc-48b9-808a-ae020c0bf535/application'}],
            'structured_job': {'hiringOrganization': {'name': 'Handshake'},
                               'jobLocation': {'address': {'addressLocality': 'San Francisco',
                                                          'addressRegion': 'California',
                                                          'addressCountry': 'United States'}}},
        }]
        jobs, summary = job_search.match_job_pages(profile, pages, now=now)
        self.assertEqual([(j['company'], j['location']) for j in jobs], [('G2', 'Bengaluru')])
        self.assertEqual(summary['rejected']['outside_location_scope'], 1)

    def test_requested_result_limit_is_never_exceeded_and_newer_ties_rank_first(self):
        profile = {'roles': ['Senior Data Analyst'], 'years_experience': 4.0,
                   'location': 'Noida, NCR, India', 'skills': ['SQL', 'Power BI']}
        pages = []
        for index in range(11):
            url = f'https://careers.example.com/job/senior-data-analyst-{index:04d}'
            pages.append({
                'url': url, 'final_url': url, 'title': f'Senior Data Analyst at Employer {index}',
                'page_title': 'Senior Data Analyst', 'content': 'Senior Data Analyst. Noida, India. Apply. SQL Power BI Python.',
                'http_status': 200, 'employer_detail_verified': True, 'posting_available': True,
                'apply_links': [{'text': 'Apply', 'url': url}],
                'structured_job': {'@type': 'JobPosting', 'title': 'Senior Data Analyst',
                                   'datePosted': f'2026-10-{15 + index:02d}',
                                   'hiringOrganization': {'name': f'Employer {index}'},
                                   'description': 'SQL Power BI Python'},
            })
        jobs, summary = job_search.match_job_pages(
            profile, pages, now=datetime.fromisoformat('2026-10-25T14:00:00+05:30'), max_results=10,
        )
        self.assertEqual(len(jobs), 10)
        self.assertEqual(summary['matching_before_limit'], 11)
        self.assertEqual(jobs[0]['posted_date'], '2026-10-25')

    def test_unconfirmed_degree_domain_and_onsite_fit_reduce_score_and_are_explained(self):
        profile = {
            'roles': ['Senior Data Analyst'], 'years_experience': 4.0,
            'location': 'Noida, NCR, India', 'education': 'B.Tech, Mechanical Engineering',
            'work_arrangement_preference': '',
            'skills': ['Excel', 'Power BI', 'Python', 'SQL', 'Tableau'],
            'text': 'Senior Data Analyst 4+ years in pharmacy benefits analytics. B.Tech Mechanical Engineering. Power BI SQL Python Tableau Excel.',
        }
        description = (
            'Senior Data Analyst. 4-7 years. Excel Power BI Python SQL Tableau. '
            'Education: Graduate/Postgraduate in Finance, Economics, Statistics, Data Analytics or related fields. '
            'Experience preferably in Mutual Funds, BFSI, or Fintech domain. '
            'Work from Office: Monday to Friday.'
        )
        page = {
            'url': 'https://valueresearch.keka.com/careers/jobdetails/408',
            'final_url': 'https://valueresearch.keka.com/careers/jobdetails/408',
            'title': 'Senior Data Analyst', 'page_title': 'Senior Data Analyst',
            'content': 'Senior Data Analyst Apply for this job', 'http_status': 200,
            'structured_job': {
                '@type': 'JobPosting', 'title': 'Senior Data Analyst',
                'hiringOrganization': {'name': 'Value Research'},
                'jobLocation': {'address': {'addressLocality': 'Noida', 'addressCountry': 'India'}},
                'description': description,
            },
            'apply_links': [{'text': 'Apply for this job', 'url': 'https://valueresearch.keka.com/careers/jobdetails/408'}],
        }
        jobs, _ = job_search.match_job_pages(profile, [page], today=job_search.date(2026, 10, 25))
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertLess(int(job['match_score'].split('/')[0]), 100)
        self.assertTrue(any('Education eligibility is unclear' in item for item in job['concerns']))
        self.assertTrue(any('Domain fit needs review' in item for item in job['concerns']))
        self.assertTrue(any('does not state willingness' in item for item in job['concerns']))
        self.assertTrue(any('points' in item for item in job['match_reasons']))

    def test_general_statistics_or_qualifications_text_does_not_create_degree_flag(self):
        penalty, concerns, _ = job_search._eligibility_adjustments(
            {'education': 'B.Tech, Mechanical Engineering', 'text': 'B.Tech Mechanical Engineering', 'work_arrangement_preference': 'On-site'},
            'Senior BI Analyst. Use statistical analysis to identify trends. Required Skills & Qualifications include SQL and Power BI.',
            'Noida, India', 'On-site',
        )
        self.assertEqual(penalty, 0)
        self.assertEqual(concerns, [])

    def test_expired_application_close_date_is_rejected(self):
        page = {
            'url': 'https://jobs.example.com/jobs/role-123456',
            'final_url': 'https://jobs.example.com/jobs/role-123456',
            'title': 'Senior Data Analyst at Example Health',
            'snippet': 'Company: Example Health',
            'content': 'Senior Data Analyst. Apply now.',
            'http_status': 200,
            'structured_job': {'@type': 'JobPosting', 'title': 'Senior Data Analyst', 'hiringOrganization': {'name': 'Example Health'}, 'description': 'Applications close on 22 September 2026.'},
            'apply_links': [{'text': 'Apply now', 'url': 'https://jobs.example.com/apply/123'}],
        }
        jobs, _ = job_search.match_job_pages({'skills': [], 'roles': ['Senior Data Analyst'], 'years_experience': 4}, [page], today=job_search.date(2026, 10, 25))
        self.assertEqual(jobs, [])

    def test_older_posting_with_active_apply_page_remains_eligible(self):
        page = {
            'url': 'https://jobs.example.com/jobs/role-123456',
            'final_url': 'https://jobs.example.com/jobs/role-123456',
            'title': 'Senior Data Analyst at Example Health',
            'content': 'Senior Data Analyst. Apply now.', 'http_status': 200,
            'structured_job': {'@type': 'JobPosting', 'title': 'Senior Data Analyst', 'datePosted': '2026-08-01', 'hiringOrganization': {'name': 'Example Health'}},
            'apply_links': [{'text': 'Apply now', 'url': 'https://jobs.example.com/apply/123'}],
        }
        jobs, _ = job_search.match_job_pages({'skills': [], 'roles': ['Senior Data Analyst'], 'years_experience': 4}, [page], today=job_search.date(2026, 10, 25))
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['company'], 'Example Health')
        self.assertEqual(jobs[0]['posted_date'], '2026-08-01')

    def test_only_destination_checked_jobs_are_included_and_closed_job_is_rejected(self):
        profile = {
            'roles': ['Senior Data Analyst', 'BI Analyst'],
            'years_experience': 4.0,
            'location': 'Noida, NCR, India',
            'skills': ['Power BI', 'SQL', 'Tableau', 'Python', 'Databricks'],
        }
        pages = [
            {
                'url': 'https://careers.example.com/senior-analyst',
                'final_url': 'https://careers.example.com/senior-analyst',
                'title': 'Senior Data Analyst at Example Health',
                'snippet': 'Company: Example Health | Location: Noida, India | 3 to 5 years experience',
                'content': 'Senior Data Analyst. Power BI SQL Tableau Python. Location Noida, India. Apply now.',
                'http_status': 200,
                'posting_available': True,
                'structured_job': {'title': 'Senior Data Analyst', 'hiringOrganization': {'name': 'Example Health'}, 'directApply': True},
                'apply_links': [{'text': 'Apply now', 'url': 'https://careers.example.com/senior-analyst/apply'}],
            },
            {
                'url': 'https://careers.example.com/closed', 'final_url': 'https://careers.example.com/closed',
                'title': 'Data Analyst at Closed Co', 'snippet': 'Company: Closed Co',
                'content': 'This role is closed.', 'http_status': 200, 'posting_available': False,
                'structured_job': {}, 'apply_links': [],
            },
            {
                'url': 'https://jobs.example.net/lead', 'title': 'BI Analyst at Unknown Co',
                'snippet': 'Power BI SQL Noida India', 'content': '', 'http_status': None,
            },
        ]
        jobs, summary = job_search.match_job_pages(profile, pages, today=job_search.date(2026, 10, 25))
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['status'], 'application page active')
        self.assertEqual(jobs[0]['url'], 'https://careers.example.com/senior-analyst/apply')
        self.assertEqual(jobs[0]['company'], 'Example Health')
        self.assertGreaterEqual(int(jobs[0]['match_score'].split('/')[0]), 70)
        self.assertEqual(jobs[0]['source'], 'careers.example.com')
        self.assertEqual(summary['verified_destinations'], 2)

    def test_search_queries_derive_from_resume_targets(self):
        queries = job_search.job_search_queries({
            'roles': ['Senior Data Analyst', 'BI Analyst'],
            'location': 'Noida, NCR, India',
            'skills': ['Power BI', 'SQL'],
        })
        self.assertEqual(len(queries), 10)
        self.assertIn('Senior Data Analyst', queries[6])
        self.assertIn('Noida, NCR, India', queries[6])
        self.assertIn('jobs.lever.co', queries[0])
        self.assertTrue(any('oraclecloud.com' in query for query in queries))
        self.assertTrue(any('job-boards.greenhouse.io' in query for query in queries))

    def test_posting_age_does_not_exclude_open_or_undated_jobs(self):
        profile = {
            'roles': ['Senior Data Analyst'], 'years_experience': 4.0,
            'location': 'Noida, NCR, India', 'skills': ['SQL', 'Power BI'],
        }
        now = datetime.fromisoformat('2026-10-25T14:00:00+05:30')
        base = {
            'title': 'Senior Data Analyst', 'page_title': 'Senior Data Analyst',
            'content': 'Senior Data Analyst. Power BI, SQL. Apply now.',
            'http_status': 200, 'posting_available': True,
            'final_url': 'https://careers.example.com/job/senior-123456',
            'url': 'https://careers.example.com/job/senior-123456',
            'apply_links': [{'text': 'Apply now', 'url': 'https://careers.example.com/job/senior-123456'}],
        }
        pages = [
            {**base, 'structured_job': {'@type': 'JobPosting', 'title': 'Senior Data Analyst',
                'datePosted': '2026-10-25T10:00:00+05:30', 'hiringOrganization': {'name': 'Recent Co'},
                'description': 'Power BI SQL'}},
            {**base, 'structured_job': {'@type': 'JobPosting', 'title': 'Senior Data Analyst',
                'datePosted': '2026-10-22', 'hiringOrganization': {'name': 'Old Co'},
                'description': 'Power BI SQL'}, 'url': 'https://careers.example.com/job/old-123456',
                'final_url': 'https://careers.example.com/job/old-123456'},
            {**base, 'structured_job': {'@type': 'JobPosting', 'title': 'Senior Data Analyst',
                'hiringOrganization': {'name': 'Undated Co'}, 'description': 'Power BI SQL'},
                'url': 'https://careers.example.com/job/unknown-123456',
                'final_url': 'https://careers.example.com/job/unknown-123456'},
        ]
        jobs, summary = job_search.match_job_pages(
            profile, pages, today=job_search.date(2026, 10, 25), max_age_hours=48, now=now,
        )
        self.assertEqual([job['company'] for job in jobs], ['Recent Co', 'Old Co', 'Undated Co'])
        self.assertEqual(summary['freshness_excluded'], 0)
        self.assertEqual(summary['freshness_unknown'], 1)

    def test_search_queries_find_open_jobs_without_a_posting_date_cutoff(self):
        queries = job_search.job_search_queries(
            {'roles': ['Senior Data Analyst'], 'location': 'Noida, India'},
            posted_within_hours=48,
        )
        self.assertEqual(len(queries), 10)
        self.assertTrue(all('currently open apply' in query for query in queries))

    def test_relative_posting_dates_are_anchored_to_retrieval_time(self):
        now = datetime.fromisoformat('2026-10-25T14:00:00+05:30')
        today = job_search._posted_datetime({}, 'Senior Analyst — Posted Today', now=now)
        yesterday = job_search._posted_datetime({}, 'Posted yesterday', now=now)
        hours_ago = job_search._posted_datetime({'search_date': '6 hours ago'}, '', now=now)
        outside = job_search._posted_datetime({'search_date': '3 days ago'}, '', now=now)
        ambient_today = job_search._posted_datetime({}, 'We keep improving the product every day, today and tomorrow.', now=now)
        self.assertEqual(today.date().isoformat(), '2026-10-25')
        self.assertEqual(yesterday.date().isoformat(), '2026-10-24')
        self.assertEqual(hours_ago.isoformat(), '2026-10-25T08:00:00+05:30')
        self.assertEqual(outside.date().isoformat(), '2026-10-22')
        self.assertIsNone(ambient_today)

    def test_candidate_discovery_ranks_individual_ats_jobs_ahead_of_hubs(self):
        from apps.jarvis.hermes_job_search import _candidate_rank
        hub = {'title': 'Data Analyst Jobs in India', 'url': 'https://boards.greenhouse.io/acme'}
        role = {'title': 'Senior Data Analyst', 'url': 'https://boards.greenhouse.io/acme/jobs/123456'}
        fresh = {'title': 'Senior Data Analyst', 'url': 'https://careers.example.com/careers/job/role-123', 'snippet': 'Posted Today. India.'}
        fresh_aggregator = {'title': 'Senior Data Analyst', 'url': 'https://campuspe.com/jobs/senior-analyst-123', 'snippet': 'Posted Today. India.'}
        self.assertGreater(_candidate_rank(role), _candidate_rank(hub))
        self.assertGreater(_candidate_rank(fresh), _candidate_rank(role))
        self.assertGreater(_candidate_rank(role), _candidate_rank(fresh_aggregator))

    def test_jobs_subdomain_is_not_assumed_to_be_an_employer(self):
        from apps.jarvis.hermes_job_search import _trusted_job_page
        self.assertFalse(_trusted_job_page('https://jobs.aconitesoft.com/jobs/senior-data-anal-ed2295b8fc'))
        self.assertTrue(_trusted_job_page('https://careers.example.com/careers/job/role-123'))

    def test_jobs_slug_detail_page_and_relative_date_can_be_verified(self):
        profile = {
            'roles': ['Senior Data Analyst'], 'years_experience': 4.0,
            'location': 'Noida, NCR, India', 'skills': ['SQL', 'Power BI'],
        }
        now = datetime.fromisoformat('2026-10-25T14:00:00+05:30')
        page = {
            'url': 'https://jobs.example.com/jobs/senior-data-analyst-abc123',
            'final_url': 'https://jobs.example.com/jobs/senior-data-analyst-abc123',
            'title': 'Senior Data Analyst', 'page_title': 'Senior Data Analyst',
            'content': 'Senior Data Analyst. Noida India. Posted Today. 3�5 years experience. SQL Power BI. Apply now.',
            'http_status': 200, 'posting_available': True,
            'apply_links': [{'text': 'Apply now', 'url': 'https://jobs.example.com/jobs/senior-data-analyst-abc123'}],
            'structured_job': {'hiringOrganization': {'name': 'Example Co'}},
        }
        jobs, _summary = job_search.match_job_pages(profile, [page], max_age_hours=48, now=now)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['company'], 'Example Co')
        self.assertEqual(jobs[0]['experience_requirement'], '3-5 years')

    def test_js_shell_with_recent_index_preview_is_labeled_provisional(self):
        profile = {
            'roles': ['Senior Data Analyst'], 'years_experience': 4.0,
            'location': 'Noida, NCR, India', 'skills': ['SQL', 'Power BI'],
        }
        now = datetime.fromisoformat('2026-10-25T14:00:00+05:30')
        page = {
            'url': 'https://careers.example.com/job/senior-analyst-12345',
            'final_url': 'https://careers.example.com/job/senior-analyst-12345',
            'title': 'Senior Data Analyst at Example Co', 'snippet': 'Senior Data Analyst at Example Co. India. Posted Today. SQL and Power BI dashboards. ' * 3,
            'content': '', 'http_status': 200, 'posting_available': None,
            'indexed_listing_evidence': True, 'apply_links': [], 'structured_job': {},
        }
        jobs, summary = job_search.match_job_pages(profile, [page], max_age_hours=48, now=now)
        self.assertEqual(len(jobs), 1)
        self.assertTrue(jobs[0]['status'].startswith('provisional'))
        self.assertTrue(any('search-index' in item for item in jobs[0]['concerns']))
        self.assertEqual(summary['verified_destinations'], 1)

    def test_employer_page_experience_overrides_conflicting_index_preview(self):
        profile = {'roles': ['Senior Data Analyst'], 'years_experience': 4.0,
                   'location': 'Noida, NCR, India', 'skills': ['SQL', 'Python', 'Power BI'],
                   'work_arrangement_preference': ''}
        now = datetime.fromisoformat('2026-10-25T14:00:00+05:30')
        page = {
            'url': 'https://boards.greenhouse.io/example/jobs/123456',
            'final_url': 'https://careers.example.com/jobs/123456',
            'title': 'Senior Data Analyst at Example Co', 'page_title': 'Senior Data Analyst',
            'snippet': 'Senior Data Analyst at Example Co. Posted Today. 5+ years experience. ' * 4,
            'content': 'Senior Data Analyst. Apply Now. 7+ years of experience. SQL Python Power BI. Gurugram, Haryana, India.',
            'http_status': 200, 'employer_detail_verified': True, 'posting_available': True,
            'indexed_listing_evidence': True,
            'apply_links': [{'text': 'Apply Now', 'url': 'https://careers.example.com/jobs/123456/apply'}],
            'structured_job': {'hiringOrganization': {'name': 'Example Co'}},
        }
        jobs, _ = job_search.match_job_pages(profile, [page], max_age_hours=48, now=now)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['experience_requirement'], '7+ years')
        self.assertEqual(jobs[0]['location'], 'Gurugram, Haryana, India')
        self.assertLessEqual(int(jobs[0]['match_score'].split('/')[0]), 55)
        self.assertTrue(jobs[0]['status'].startswith('provisional'))

    def test_employer_career_slug_and_company_domain_are_recognized(self):
        profile = {'roles': ['Senior Data Analyst'], 'years_experience': 4.0,
                   'location': 'Noida, NCR, India', 'skills': ['SQL', 'Python', 'Power BI']}
        now = datetime.fromisoformat('2026-10-25T14:00:00+05:30')
        page = {
            'url': 'https://jobs.neuradeskai.com/jobs/at/okta/7731263',
            'final_url': 'https://www.okta.com/company/careers/ga/senior-data-analyst-7731263/',
            'title': 'Senior Data Analyst', 'page_title': 'Senior Data Analyst',
            'snippet': 'Senior Data Analyst at Okta. Bengaluru, India. Posted today. SQL Python Power BI. ' * 4,
            'content': 'Senior Data Analyst. SQL Python Power BI. Bengaluru, India. 4+ years experience.',
            'http_status': 200, 'employer_detail_verified': True,
            'indexed_listing_evidence': True, 'posting_available': True,
            'apply_links': [{'text': 'Apply now', 'url': 'https://www.okta.com/company/careers/ga/senior-data-analyst-7731263/'}],
            'structured_job': {},
        }
        jobs, _ = job_search.match_job_pages(profile, [page], max_age_hours=48, now=now)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['company'], 'Okta')
        self.assertEqual(jobs[0]['title'], 'Senior Data Analyst')

    def test_old_posting_date_is_kept_and_not_overridden_by_fresh_search_snippet(self):
        profile = {'roles': ['Senior Data Analyst'], 'years_experience': 4.0,
                   'location': 'Noida, NCR, India', 'skills': ['SQL', 'Python', 'Power BI']}
        now = datetime.fromisoformat('2026-10-25T14:00:00+05:30')
        page = {
            'url': 'https://www.okta.com/company/careers/ga/senior-data-analyst-7731263/',
            'final_url': 'https://www.okta.com/company/careers/ga/senior-data-analyst-7731263/',
            'title': 'Senior Data Analyst', 'page_title': 'Senior Data Analyst',
            'snippet': 'Senior Data Analyst. Posted Today. SQL, Python, Power BI. ' * 4,
            'content': 'Senior Data Analyst. Posted on Sep 28, 2026. SQL Python Power BI. Apply Now.',
            'http_status': 200, 'employer_detail_verified': True,
            'indexed_listing_evidence': True, 'posting_available': True,
            'apply_links': [{'text': 'Apply Now', 'url': 'https://www.okta.com/company/careers/ga/senior-data-analyst-7731263/'}],
            'structured_job': {},
        }
        jobs, summary = job_search.match_job_pages(profile, [page], max_age_hours=48, now=now)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['posted_date'], '2026-09-28')
        self.assertEqual(summary['freshness_excluded'], 0)


if __name__ == '__main__':
    unittest.main()
