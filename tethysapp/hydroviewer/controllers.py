from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from tethys_sdk.gizmos import SelectInput, ToggleSwitch, Button

import requests
import json
import datetime as dt
import time
import netCDF4 as nc
import numpy as np

@login_required()
def home(request):
    model_input = SelectInput(display_text='',
                              name='model',
                              multiple=False,
                              options=[('Select Model', ''), ('ECMWF-RAPID', 'ecmwf'), ('LIS-RAPID', 'lis')],
                              initial=['Select Model'],
                              original=True)

    context = {
        'model_input': model_input,
    }

    return render(request, 'hydroviewer/home.html', context)


@login_required()
def ecmwf(request):
    model_input = SelectInput(display_text='',
                              name='model',
                              multiple=False,
                              options=[('Select Model', ''), ('ECMWF-RAPID', 'ecmwf'), ('LIS-RAPID', 'lis')],
                              initial=['ecmwf'],
                              original=True)

    res = requests.get('https://tethys.byu.edu/apps/streamflow-prediction-tool/api/GetWatersheds/',
                       headers={'Authorization': 'Token 72b145121add58bcc5843044d9f1006d9140b84b'})

    watershed_list_raw = json.loads(res.content)
    watershed_list = [value for value in watershed_list_raw if "Nepal" in value[0] or "NEPAL" in value[0] or "nepal" in value[0]]
    watershed_list.append(['Select Watershed', ''])

    watershed_select = SelectInput(display_text='',
                                   name='watershed',
                                   options=watershed_list,
                                   initial=['Select Watershed'],
                                   original=True)

    context = {
        'model_input': model_input,
        'watershed_select': watershed_select
    }

    return render(request, 'hydroviewer/ecmwf.html', context)


@login_required()
def lis(request):
    model_input = SelectInput(display_text='',
                              name='model',
                              multiple=False,
                              options=[('Select Model', ''), ('ECMWF-RAPID', 'ecmwf'), ('LIS-RAPID', 'lis')],
                              initial=['LIS-RAPID'],
                              original=True)

    watershed_list = [['Nepal (Bagmati)', 1], ['Select Watershed', '']]
    watershed_select = SelectInput(display_text='',
                                   name='watershed',
                                   options=watershed_list,
                                   initial=['Select Watershed'],
                                   original=True)

    context = {
        'model_input': model_input,
        'watershed_select': watershed_select
    }

    return render(request, 'hydroviewer/lis.html', context)


def ecmwf_get_time_series(request):
    get_data = request.GET

    try:
        model = get_data['model']
        watershed = get_data['watershed']
        subbasin = get_data['subbasin']
        comid = get_data['comid']
        if get_data['startdate'] != '':
            startdate = get_data['startdate']
        else:
            startdate = 'most_recent'

        if model == 'ecmwf-rapid':
            res = requests.get('https://tethys.byu.edu/apps/streamflow-prediction-tool/api/GetWaterML/?watershed_name=' +
                               watershed + '&subbasin_name=' + subbasin + '&reach_id=' + comid + '&start_folder=' +
                               startdate + '&stat_type=mean', headers={'Authorization': 'Token 72b145121add58bcc5843044d9f1006d9140b84b'})

            api_call = res.content
            data = api_call.split('dateTimeUTC="')
            data.pop(0)

            ts_pairs = []
            for elem in data:
                date = time.mktime(dt.datetime.strptime(elem.split('"  methodCode="1"  sourceCode="1"  qualityControlLevelCode="1" >')[0],
                                                        '%Y-%m-%dT%H:%M:%S').timetuple())
                value = float(elem.split('  methodCode="1"  sourceCode="1"  qualityControlLevelCode="1" >')[1].split('</value>')[0])

                ts_pairs.append([date * 1e3, value])

            ts_pairs_data = {}
            ts_pairs_data['watershed'] = watershed
            ts_pairs_data['subbasin'] = subbasin
            ts_pairs_data['id'] = comid
            ts_pairs_data['ts_pairs'] = ts_pairs

            return JsonResponse({
                "success": "Data analysis complete!",
                "ts_pairs_data": json.dumps(ts_pairs_data)
            })

    except Exception as e:
        print str(e)
        return JsonResponse({'error': 'No data found for the selected reach.'})


def lis_get_time_series(request):
    get_data = request.GET

    try:
        model = get_data['model']
        watershed = get_data['watershed']
        subbasin = get_data['subbasin']
        comid = get_data['comid']

        if model == 'lis-rapid':
            res = nc.Dataset('/rapid/lis/' + watershed + '-' + subbasin + '/Qout_nasa_lis_72hr_20150801to20150831.nc')

            dates = res.variables['time'][:] * 1e3

            comid_list = res.variables['rivid'][:]
            comid_index = int(np.where(comid_list == int(comid))[0])

            values = []
            for l in list(res.variables['Qout'][:]):
                values.append(float(l[comid_index]))
                print type(l[comid_index])

            ts_pairs = [list(a) for a in zip(dates, values)]

            ts_pairs_data = {}
            ts_pairs_data['watershed'] = watershed
            ts_pairs_data['subbasin'] = subbasin
            ts_pairs_data['id'] = comid
            ts_pairs_data['ts_pairs'] = ts_pairs

            return JsonResponse({
                "success": "Data analysis complete!",
                "ts_pairs_data": json.dumps(ts_pairs_data)
            })

    except Exception as e:
        print str(e)
        return JsonResponse({'error': 'No data found for the selected reach.'})


def get_available_dates(request):
    get_data = request.GET

    watershed = get_data['watershed']
    subbasin = get_data['subbasin']

    res = requests.get('https://tethys.byu.edu/apps/streamflow-prediction-tool/api/GetAvailableDates/?watershed_name=' + watershed +
                       '&subbasin_name=' + subbasin, headers={'Authorization': 'Token 72b145121add58bcc5843044d9f1006d9140b84b'})

    dates = []
    for date in eval(res.content):
        if len(date) == 10:
            date_mod = date + '000'
            date_f = dt.datetime.strptime(date_mod , '%Y%m%d.%H%M').strftime('%Y-%m-%d %H:%M')
        else:
            date_f = dt.datetime.strptime(date, '%Y%m%d.%H%M').strftime('%Y-%m-%d %H:%M')
        dates.append([date_f, date])

    dates.append(['Select Date', dates[-1][1]])
    dates.reverse()

    return JsonResponse({
        "success": "Data analysis complete!",
        "available_dates": json.dumps(dates)
    })


def get_return_periods(request):
    get_data = request.GET

    watershed = get_data['watershed']
    subbasin = get_data['subbasin']
    comid = get_data['comid']

    res = requests.get('https://tethys.byu.edu/apps/streamflow-prediction-tool/api/GetReturnPeriods/?watershed_name=' + watershed +
                       '&subbasin_name=' + subbasin + '&reach_id=' + comid,
                       headers={'Authorization': 'Token 72b145121add58bcc5843044d9f1006d9140b84b'})

    return JsonResponse({
        "return_periods": eval(res.content)
    })
