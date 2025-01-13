Dynamic MFA results

| Results                                                                    | Explanation                                                                                                                           | Example                                                                                                 |
|----------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| stock_by_cohort (x_stock_by_cohort)                                        | provides the stock, segmented by their introduction year into the system                                                              | Wood introduced in the stock in the year x, may still be accounted for within the same stock in year y. |
| total or in-use stock (x_stock_total)                                      | reflects the aggregate stock within the system,snapshot of total material quantities at any given time   offering a                   |                                                                                                         |
| stock change (x_stock_change)                                              | denotes the net changes in stock within the system over time, capturing dynamic shifts in stock levels                                |                                                                                                         |
| total outflow (x_o)last year of flows)                                     | reports the total outflows from the stock, providing an overarching value that reflects total material loss from the system over time | Provides insights, for example, on the total wood outflow from a stock in year x.                       |
| outflow by cohort (x_oc)                                                   | indicates the outflow of materials for each cohort as they reach the end of their lifespan                                            |                                                                                                         |
| Net annual co2 emissions and removals (results_net_co2_emissions_removals) | calculated by using the stock change results and converting them to CO2 equivalents                                                   | Provides insights on the amount of CO2 stocked within the products per year                             |




:::{note}
For Net annual co2 emissions and removals, ff the result of the stock change is positive, it indicates an increase in carbon stocks, which corresponds  to a net removal of CO2 from the atmosphere. If the result is negative, it indicates a decrease in carbon
stocks, corresponding to net CO2 emissions to the atmosphere.
:::

:::{dropdown} <span style="font-weight: normal; font-style: italic;">Again, here's the code in case you're interested</span>
:icon: codescan

