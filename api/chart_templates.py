def get_base_pie_chart_config():
    return {
        'type': 'pie',
        'data': {
            'labels': [],
            'datasets': [{
                'data': [],
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(153, 102, 255, 0.7)',
                    'rgba(255, 159, 64, 0.7)',
                    'rgba(199, 199, 199, 0.7)',
                    'rgba(83, 102, 255, 0.7)',
                    'rgba(102, 255, 83, 0.7)'
                ],
                'borderColor': 'rgba(255, 255, 255, 0.1)',
                'borderWidth': 1
            }]
        },
        'options': {
            'responsive': True,
            'plugins': {
                'legend': {
                    'position': 'top',
                    'labels': {
                        'font': {
                            'size': 10
                        },
                        'padding': 10
                    }
                },
                'title': {
                    'display': True,
                    'text': '',
                    'font': {
                        'size': 14
                    },
                    'padding': {
                        'top': 10,
                        'bottom': 15
                    }
                },
                'datalabels': {
                    'display': True,
                    'color': 'white',
                    'font': {
                        'weight': 'bold',
                        'size': 10,
                    },
                    'formatter': "(value, ctx) => { return value; }"
                }
            }
        }
    }


def get_base_bar_chart_config():
    return {
        'type': 'bar',
        'data': {
            'labels': [],
            'datasets': [{
                'label': '',
                'data': [],
                'backgroundColor': 'rgba(75, 192, 192, 0.7)',
                'borderColor': 'rgba(75, 192, 192, 1)',
                'borderWidth': 1
            }]
        },
        'options': {
            'responsive': True,
            'plugins': {
                'legend': {
                    'display': True,
                    'position': 'top',
                },
                'title': {
                    'display': True,
                    'text': '',
                    'font': {'size': 14},
                    'padding': {'top': 10, 'bottom': 15}
                }
            },
            'scales': {
                'yAxes': [{
                    'ticks': {
                        'beginAtZero': True,
                        'stepSize': 1
                    }
                }],
                'xAxes': [{
                    'ticks': {
                        'font': {'size': 10}
                    }
                }]
            }
        }
    }


def get_base_line_chart_config():
    return {
        'type': 'line',
        'data': {
            'labels': [],
            'datasets': [{
                'label': '',
                'data': [],
                'borderColor': 'rgba(54, 162, 235, 0.9)',
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'fill': True,
                'tension': 0.1
            }]
        },
        'options': {
            'responsive': True,
            'plugins': {
                'legend': {
                    'display': True,
                    'position': 'top',
                },
                'title': {
                    'display': True,
                    'text': '',
                    'font': {'size': 14},
                    'padding': {'top': 10, 'bottom': 15}
                }
            },
            'scales': {
                'yAxes': [{'ticks': {'beginAtZero': True}}],
                'xAxes': [{'ticks': {'font': {'size': 10}}}]
            }
        }
    }
