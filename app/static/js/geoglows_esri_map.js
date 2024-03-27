////////////////////////////////////////////////////////////////////////  ESRI LAYER ANIMATION CONTROLS
let layerAnimationTime = new Date();
layerAnimationTime = new Date(layerAnimationTime.toISOString())
layerAnimationTime.setUTCHours(0);
layerAnimationTime.setUTCMinutes(0);
layerAnimationTime.setUTCSeconds(0);
layerAnimationTime.setUTCMilliseconds(0);
const currentDate = $("#current-map-date");
const startDateTime = new Date(layerAnimationTime);
const endDateTime = new Date(layerAnimationTime.setUTCHours(5 * 24));
layerAnimationTime = new Date(startDateTime);
currentDate.html(layerAnimationTime);
const slider = $("#time-slider");
slider.change(function () {
    refreshLayerAnimation()
})

function refreshLayerAnimation() {
    layerAnimationTime = new Date(startDateTime);
    layerAnimationTime.setUTCHours(slider.val() * 3);
    currentDate.html(layerAnimationTime);
    globalLayer.setTimeRange(layerAnimationTime, endDateTime);
}

let animate = false;

function playAnimation(once = false) {
    if (!animate) {
        return
    }
    if (layerAnimationTime < endDateTime) {
        slider.val(Number(slider.val()) + 1)
    } else {
        slider.val(0)
    }
    refreshLayerAnimation();
    if (once) {
        animate = false;
        return
    }
    setTimeout(playAnimation, 750);
}

$("#animationPlay").click(function () {
    animate = true;
    playAnimation()
})
$("#animationStop").click(function () {
    animate = false;
})
$("#animationPlus1").click(function () {
    animate = true;
    playAnimation(true)
})
$("#animationBack1").click(function () {
    if (layerAnimationTime > startDateTime) {
        slider.val(Number(slider.val()) - 1)
    } else {
        slider.val(40)
    }
    refreshLayerAnimation();
})
////////////////////////////////////////////////////////////////////////  FUNCTIONS FOR MAP INTERACTION
function clearChartDivs() {
    fc.html('');
    hc.html('');
}

function updateStatusIcons(type) {
    let statusObj = $("#request-status");
    if (type === 'identify') {
        statusObj.html(' (Getting Stream ID)');
        statusObj.css('color', 'orange');
    } else if (type === 'load') {
        statusObj.html(' (Loading ID ' + reach_id + ')');
        statusObj.css('color', 'orange');
    } else if (type === 'ready') {
        statusObj.html(' (Ready)');
        statusObj.css('color', 'green');
    } else if (type === 'fail') {
        statusObj.html(' (Failed)');
        statusObj.css('color', 'red');
    } else if (type === 'cleared') {
        statusObj.html(' (Cleared)');
        statusObj.css('color', 'grey');
    }
}

function updateDownloadLinks(type) {
    if (type === 'clear') {
        $("#download-forecast-btn").attr('href', '');
    } else if (type === 'set') {
        $("#download-forecast-btn").attr('href', endpoint + 'ForecastStats/?reach_id=' + reach_id);
    }
}

function plotForecastStats(id) {
    forecastsLoaded = false;
    $.ajax({
        type: 'GET',
        async: true,
        url: endpoint + 'ForecastStats/?return_format=json&reach_id=' + id,
        success: function (data) {
            fc.html('');
            let ts = data['time_series']
            let dt_rv = ts['datetime'].concat(ts['datetime'].slice().reverse());
            let traces = [
                {
                    name: 'Max/Min Flow (m^3/s)',
                    x: dt_rv,
                    y: ts['flow_max_m^3/s'].concat(ts['flow_min_m^3/s'].slice().reverse()),
                    mode: 'lines',
                    type: 'scatter',
                    fill: 'toself',
                    fillcolor: 'lightblue',
                    line: {color: 'darkblue', dash: 'dash'},
                },
                {
                    name: '25-75% Flow (m^3/s)',
                    x: dt_rv,
                    y: ts['flow_75%_m^3/s'].concat(ts['flow_25%_m^3/s'].slice().reverse()),
                    mode: 'lines',
                    type: 'scatter',
                    fill: 'toself',
                    fillcolor: 'lightgreen',
                    line: {color: 'darkgreen', dash: 'dash'},
                },
                {
                    name: 'Average Flow (m^3/s)',
                    x: ts['datetime'],
                    y: ts['flow_avg_m^3/s'],
                    mode: 'lines',
                    type: 'scatter',
                    fill: 'none',
                    line: {color: 'blue'},
                },
                {
                    name: 'High Res Flow (m^3/s)',
                    x: ts['datetime_high_res'],
                    y: ts['high_res'],
                    mode: 'lines',
                    type: 'scatter',
                    fill: 'none',
                    line: {color: 'black'},
                },
            ]
            Plotly.newPlot('forecast-chart', traces, {title: 'Forecasted Flow<br>Reach ID: ' + reach_id});
            forecastsLoaded = true;
            updateStatusIcons('ready');
            updateDownloadLinks('set');
        },
        error: function () {
            console.log('forecast fail');
            updateStatusIcons('fail');
            clearChartDivs();
        }
    })
}

function mapClickEvent(event) {
    if (map.getZoom() <= 9.5) {
        map.flyTo(event.latlng, 10);
        return
    } else {
        map.flyTo(event.latlng)
    }
    if (marker) {
        map.removeLayer(marker)
    }
    marker = L.marker(event.latlng).addTo(map);
    $("#chart_modal").modal('show');
    updateStatusIcons('identify');
    L.esri.identifyFeatures({
        url: 'https://livefeeds2.arcgis.com/arcgis/rest/services/GEOGLOWS/GlobalWaterModel_Medium/MapServer'
    })
        .on(map)
        .at([event.latlng['lat'], event.latlng['lng']])
        .tolerance(10)  // map pixels to buffer search point
        .precision(3)  // decimals in the returned coordinate pairs
        .run(function (error, featureCollection) {
            if (error) {
                updateStatusIcons('fail');
                alert('Error finding the reach_id');
                return
            }
            SelectedSegment.clearLayers();
            SelectedSegment.addData(featureCollection.features[0].geometry)
            reach_id = featureCollection.features[0].properties["COMID (Stream Identifier)"];
            clearChartDivs();
            updateStatusIcons('load');
            updateDownloadLinks('clear');
            plotForecastStats(reach_id);
        })
}
////////////////////////////////////////////////////////////////////////  MAKE THE MAP
const map = L.map('map', {
    zoom: 2,
    minZoom: 2,
    boxZoom: true,
    maxBounds: L.latLngBounds(L.latLng(-100, -225), L.latLng(100, 225)),
    center: [20, 0],
});
const basemap = L.esri.basemapLayer('Topographic').addTo(map);
const globalLayer = L.esri.dynamicMapLayer({
    url: 'https://livefeeds2.arcgis.com/arcgis/rest/services/GEOGLOWS/GlobalWaterModel_Medium/MapServer',
    useCors: false,
    layers: [0],
    from: startDateTime,
    to: endDateTime,
}).addTo(map);

let marker = null;
let SelectedSegment = L.geoJSON(false, {weight: 5, color: '#00008b'}).addTo(map);
const endpoint = "https://geoglows.ecmwf.int/api/"
const fc = $("#forecast-chart");
const hc = $("#historical-chart");
const ftl = $("#forecast_tab_link");
const htl = $("#historical_tab_link");
let forecastsLoaded, historicalLoaded = false;
let reach_id;
const modal_toggles = L.control({position: 'bottomright'});
modal_toggles.onAdd = function () {
    let div = L.DomUtil.create('div');
    div.innerHTML = '<div id="modal_toggles" style="text-align: right;">' +
        '<button id="show_modal_btn" class="btn btn-lg btn-warning" data-toggle="modal" data-target="#chart_modal">View Results</button>' +
        '</div>';
    return div
};
modal_toggles.addTo(map);
const mt = $("#modal_toggles");
mt.mouseover(function () {
    map.off('click')
})
mt.mouseout(function () {
    map.on("click", function (event) {
        mapClickEvent(event)
    })
});
map.on("click", function (event) {
    mapClickEvent(event)
});
