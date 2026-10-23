"""HTTP seam: the Recruiter roster that feeds the switcher."""


async def test_recruiters_lists_the_seeded_roster(client):
    response = await client.get("/api/v1/recruiters")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "R-101", "full_name": "Dana Whitmore", "role": "admin", "regions": ["*"]},
        {"id": "R-102", "full_name": "Caleb Nguyen", "role": "recruiter", "regions": ["US-MW", "US-NE"]},
        {"id": "R-103", "full_name": "Marisol Vega", "role": "recruiter", "regions": ["PH-MNL", "CO-BOG"]},
        {"id": "R-104", "full_name": "Jordan Blake", "role": "recruiter", "regions": ["US-W", "US-SE"]},
        {"id": "R-105", "full_name": "Tessa Iqbal", "role": "recruiter", "regions": ["US-NE"]},
    ]
