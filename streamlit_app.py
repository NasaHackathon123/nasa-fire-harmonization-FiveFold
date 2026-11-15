"""Streamlit Community Cloud entry point. NASA credentials stay in Python."""
import os
import streamlit as st

st.set_page_config(page_title='EmberWatch · NASA Fire Observatory', layout='wide')
# Root-level Streamlit secrets become environment variables in Community Cloud.
try:
    if st.secrets.get('FIRMS_MAP_KEY'):
        os.environ['FIRMS_MAP_KEY'] = str(st.secrets['FIRMS_MAP_KEY'])
except FileNotFoundError:
    pass  # Local development uses the existing server .env.

from backend.app.services.dashboard import build_payload, refresh_recent, render_dashboard
from fastapi import HTTPException


@st.cache_data(ttl=3600, show_spinner=False)
def dashboard():
    notice = None
    if os.environ.get('FIRMS_MAP_KEY', '').strip():
        try:
            refresh_recent()
        except (HTTPException, ValueError, KeyError):
            notice = 'NASA refresh is temporarily unavailable. Displaying the last cached observations when available.'
    else:
        notice = 'Set FIRMS_MAP_KEY in Streamlit Secrets to enable NASA downloads.'
    try:
        payload = build_payload()
    except HTTPException:
        # Never keep a transient lock failure for an hour.
        raise RuntimeError('Data cache is busy. Reload this page shortly.') from None
    return render_dashboard(payload), notice


with st.spinner('Loading NASA satellite observations…'):
    try:
        html, notice = dashboard()
    except RuntimeError:
        st.info('Data cache is busy. Reload this page shortly.')
        st.stop()
if notice:
    st.warning(notice)
st.iframe(html, height=1500)
st.caption('Data is shared across visitors and refreshed on the first visit after one hour. NASA FIRMS observations are not confirmed wildfire incidents.')
