# COVID-19 Dashboard & Deployment using Plotly Dash and Heroku

This repository includes the source code for a COVID-19 dashboard created using Plotly Dash. The dashboard is deployed via [Heroku](https://www.heroku.com/).

## Dashboard content

The COVID-19 Dashboard (deployed [here](https://worldcovidcases.herokuapp.com/)) includes cumulative total cases and daily cases over time (2020) from 190 countries across 6 continents. The dashboard also shows high-level metrics such as total cases, deaths, tests, and hospital patients per geographical region, as well as top-N country with respect to a certain metric.

## Data

The [data](https://github.com/owid/covid-19-data/tree/master/public/data) used in generating the visualizations in the dashboard is taken from [Our World In Data](https://ourworldindata.org/coronavirus). The data is regularly maintained by said organization. The data is updated after every update to the Heroku deployment.

## About me
[My website](https://www.anhtran.nl/)
[My Linkedin](https://www.linkedin.com/in/atranto/)

## How to deploy the dashboard

1. [Fork this repository.](https://github.com/at-nl/dash-demo1/fork)
2. Create a Heroku account on [Heroku](https://www.heroku.com/).
3. Create a new web app on Heroku and link it to the forked repository.
4. Deploy the `main` branch of the forked repository on Heroku.
5. Go to the URL generated on Heroku to view the deployed dashboard.


