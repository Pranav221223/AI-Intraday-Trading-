function renderAccuracyChart(accuracyData) {
    // Create trend indicators
    const trendMarkers = accuracyData.trends.map(trend => 
        trend > 0 ? 'arrow-up' : 'arrow-down'
    );
    
    const trace1 = {
        x: accuracyData.dates,
        y: accuracyData.actual,
        name: 'Actual',
        line: {color: '#4a6bff', width: 3},
        mode: 'lines+markers',
        marker: {
            size: 8,
            color: '#4a6bff',
            line: {width: 1, color: 'white'}
        }
    };
    
    const trace2 = {
        x: accuracyData.dates,
        y: accuracyData.predicted,
        name: 'Predicted',
        line: {color: '#10b981', width: 3},
        mode: 'lines+markers',
        marker: {
            size: 8,
            color: '#10b981',  // Single color
            line: {width: 1, color: 'white'}
        }
    };
    
    const layout = {
        margin: {t: 0, b: 30, l: 40, r: 20},
        showlegend: false,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        xaxis: {
            showgrid: false,
            tickfont: {size: 10, color: '#94a3b8'}
        },
        yaxis: {
            showgrid: true,
            gridcolor: 'rgba(74, 107, 255, 0.1)',
            tickfont: {size: 10, color: '#94a3b8'}
        },
        hovermode: 'x unified',
        hoverlabel: {
            bgcolor: 'rgba(20, 26, 45, 0.9)',
            font: {color: 'white'}
        },
        transition: {
            duration: 500,
            easing: 'cubic-in-out'
        }
    };
    
    Plotly.newPlot(
        document.querySelector('.accuracy-chart'),
        [trace1, trace2],
        layout,
        {displayModeBar: false}
    );
    
    // Add smooth animation on load
    // Plotly.animate(
    //     document.querySelector('.accuracy-chart'),
    //     {
    //         data: [{y: accuracyData.actual}, {y: accuracyData.predicted}],
    //         traces: [0, 1],
    //         layout: {}
    //     },
    //     {
    //         transition: {
    //             duration: 1000,
    //             easing: 'cubic-in-out'
    //         },
    //         frame: {
    //             duration: 500,
    //             redraw: false
    //         }
    //     }
    // );
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Make 3D plot responsive
    function resizePlots() {
        if (typeof Plotly !== 'undefined') {
            const plotContainers = document.querySelectorAll('.chart-container');
            plotContainers.forEach(container => {
                if (container.querySelector('.plotly-graph-div')) {
                    Plotly.Plots.resize(container.querySelector('.plotly-graph-div'));
                }
            });
        }
    }

    // Initial resize
    resizePlots();
    
    // Resize on window change
    window.addEventListener('resize', resizePlots);
    
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Animate metric cards on scroll
    const observerOptions = {
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.metric-card').forEach(card => {
        observer.observe(card);
    });

    if (typeof accuracyData !== 'undefined') {
        renderAccuracyChart(accuracyData);
    }
});