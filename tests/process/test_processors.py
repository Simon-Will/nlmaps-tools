from pathlib import Path

import pytest
from OSMPythonTools.cachingStrategy import CachingStrategy, JSON

from nlmaps_tools.answer_overpass import MultiAnswer, DistAnswer, MapAnswer, ListAnswer
from nlmaps_tools.parse_mrl import Symbol
from nlmaps_tools.process import ProcessingTool, ProcessingRequest
from nlmaps_tools.process.processors import PROCESSORS

# These tests should be more fine-grained, but who has the time.

@pytest.fixture
def nominatim_and_overpass_cache(monkeypatch):
    # Instead of mocking Overpass and Nominatim, we just make use of the caching feature.
    cache_dir = Path(__file__).parent / "cache"
    monkeypatch.setattr(CachingStrategy, "_CachingStrategy__strategy", JSON(cacheDir=cache_dir))


@pytest.mark.parametrize(
    ["lin", "expected_features_after_nwr_name_lookup", "expected_multi_answer"],
    [
        (
            "query@3 area@1 keyval@2 name@0 Heidelberg@s nwr@1 keyval@2 drink:absinthe@0 yes@s qtype@1 latlong@0",
            {
                "area": "Heidelberg",
                "target_nwr": (("drink:absinthe", "yes"),),
                "query_type": "in_query",
                "qtype": (Symbol("latlong"),),
                "area_id": 3600285864,
            },
            MultiAnswer(
                answers=[MapAnswer(type="map")],
                targets={
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [8.7073364, 49.4122262],
                            },
                            "properties": {
                                "popupContent": "<b>Sonderbar</b><br>lat: 49.4122262 lon: 8.7073364<br>addr:city: Heidelberg<br>addr:housenumber: 13<br>addr:postcode: 69117<br>addr:street: Untere Straße<br>alt_name: Betreutes Trinken<br>amenity: pub<br>beer_€: 3,00<br>drink:absinthe: yes<br>happy_hours: no<br>internet_access: unknown<br>menu_languages: german<br>name: Sonderbar<br>number_of_menulanguages: 1<br>old_name: Pinte<br>opening_hours: Mo-Th 14:00-02:00, Fr-Sa 14:00-03:00; Su 14:00-02:00<br>outdoor_seating: yes<br>payment:cash: yes<br>phone: +49 6221 25200<br>smoking: dedicated<br>toilets:wheelchair: no<br>wheelchair: yes"
                            },
                        },
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [8.7072591, 49.4121049],
                            },
                            "properties": {
                                "popupContent": "<b>Grüner Engel Absinthe</b><br>lat: 49.4121049 lon: 8.7072591<br>addr:city: Heidelberg<br>addr:housenumber: 14<br>addr:postcode: 69117<br>addr:street: Untere Straße<br>drink:absinthe: yes<br>drive_through: no<br>lastcheck: 2017-08-08<br>name: Grüner Engel Absinthe<br>opening_hours: 12:00- 21:00; Su,Ph off<br>operator: LogisticX GmbH & Co. KG<br>phone: +49 6221 4339230<br>shop: alcohol<br>toilets:wheelchair: no<br>website: https://www.absinthehouse.com/de/gruener-engel.html<br>wheelchair: no"
                            },
                        },
                    ],
                },
                centers=None,
            ),
        ),
        (
            "query@2 around@4 center@2 area@1 keyval@2 name@0 New€York€City@s nwr@1 keyval@2 name@0 Pilgrim€Hill@s search@1 nwr@1 keyval@2 amenity@0 fountain@s maxdist@1 DIST_INTOWN@0 topx@1 1@0 qtype@1 findkey@1 name@s",
            {
                "area": "New York City",
                "center_nwr": [("way", 393449121)],
                "target_nwr": (("amenity", "fountain"),),
                "maxdist": Symbol("DIST_INTOWN"),
                "around_topx": Symbol("1"),
                "query_type": "around_query",
                "qtype": (("findkey", "name"),),
                "area_id": 3600175905,
            },
            MultiAnswer(
                answers=[
                    ListAnswer(type="list", list=["way 958635828: Bethesda Fountain"])
                ],
                targets={
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [-73.97083265, 40.774315900000005],
                            },
                            "properties": {
                                "popupContent": "<b>Bethesda Fountain</b><br>lat: None lon: None<br>alt_name: Angel of the Waters<br>amenity: fountain<br>artist:wikidata: Q1338103<br>artist:wikipedia: en:Emma Stebbins<br>artist_name: Emma Stebbins<br>artwork_type: statue<br>drinking_water: no<br>fountain: decorative<br>lit: yes<br>name: Bethesda Fountain<br>natural: water<br>start_date: 1873-05-31<br>subject: Angel of the Waters<br>tourism: attraction<br>website: https://www.centralparknyc.org/locations/bethesda-fountain<br>website:alternate: https://www.nycgovparks.org/parks/central-park/monuments/114<br>wikidata: Q532029<br>wikipedia: en:Bethesda Fountain"
                            },
                        }
                    ],
                },
                centers={
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [-73.96827855000001, 40.77352005],
                            },
                            "properties": {
                                "popupContent": "<b>Pilgrim Hill</b><br>lat: None lon: None<br>landuse: grass<br>name: Pilgrim Hill<br>website: https://www.centralparknyc.org/locations/pilgrim-hill"
                            },
                        }
                    ],
                },
            ),
        ),
        (
            "dist@2 query@2 nwr@1 keyval@2 name@0 new€york@s qtype@1 latlong@0 query@3 area@1 keyval@2 name@0 izmir@s nwr@1 keyval@2 name@0 ephesus@s qtype@1 latlong@0",
            {
                "sub": [
                    {
                        "target_nwr": [("relation", 175905)],
                        "query_type": "in_query",
                        "qtype": (Symbol("latlong"),),
                    },
                    {
                        "area": "izmir",
                        "target_nwr": [("node", 7083393810)],
                        "query_type": "in_query",
                        "qtype": (Symbol("latlong"),),
                        "area_id": 3600223167,
                    },
                ],
                "query_type": "dist",
            },
            MultiAnswer(
                answers=[
                    DistAnswer(
                        type="dist",
                        dist=8195.661651439314,
                        target=(7083393810, "Ephesus"),
                        center=(175905, "City of New York"),
                    )
                ],
                targets={
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [27.3437775, 37.9443103],
                            },
                            "properties": {
                                "popupContent": "<b>Ephesus</b><br>lat: 37.9443103 lon: 27.3437775<br>access: private<br>historic: archaeological_site<br>historic:civilization: ancient_greek<br>inscription: Ephesus (/ˈɛfəsəs/;Ancient Greek: Ἔφεσος Efesos;Turkish: Efes;may ultimately derive from Hittite Apasa) was an ancient Greek city on the coast of Ionia, three kilometres southwest of present-day Selçuk in İzmir Province, Turkey.<br>name: Ephesus<br>wikidata: Q47611<br>wikipedia: en:Ephesus"
                            },
                        }
                    ],
                },
                centers={
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [-73.97953799999999, 40.697104],
                            },
                            "properties": {
                                "popupContent": "<b>City of New York</b><br>lat: None lon: None<br>admin_level: 5<br>alt_name: New York City<br>alt_name:it: Nuova York<br>alt_name:pt: Cidade de Nova Iorque<br>alt_name:vi: Thành phố New York;Thành phố Nữu Ước;Thành phố Nữu Ước;Niu Oóc;Thành phố Niu Oóc<br>border_type: city<br>boundary: administrative<br>gnis:feature_id: 2395220<br>is_in:country_code: US<br>is_in:state: New York<br>is_in:state_code: NY<br>loc_name: Big Apple<br>name: City of New York<br>name:ar: نيويورك<br>name:be: Нью-Ёрк<br>name:be-tarask: Нью-Ёрк<br>name:br: Evrog Nevez<br>name:ca: Nova York<br>name:cs: New York<br>name:cy: Efrog Newydd<br>name:de: New York<br>name:el: Νέα Υόρκη<br>name:en: New York<br>name:eo: Novjorko<br>name:es: Nueva York<br>name:fa: نیویورک<br>name:fr: New York<br>name:gl: Nova York<br>name:he: ניו יורק<br>name:hi: न्यूयॊर्क्<br>name:is: Nýja Jórvík<br>name:it: New York<br>name:ja: ニューヨーク<br>name:jbo: .nu,IORK.<br>name:kn: ನ್ಯೂಯೊರ್ಕ್<br>name:ko: 뉴욕<br>name:oc: Nòva York<br>name:pl: Nowy Jork<br>name:pt: Nova Iorque<br>name:ru: Нью-Йорк<br>name:te: న్యూయొర్క్<br>name:uk: Нью-Йорк<br>name:vi: New York<br>name:zh: 纽约/紐約<br>name:zh-Hans: 纽约<br>name:zh-Hant: 紐約<br>nist:fips_code: 3608151000<br>old_name:cs: Nový York<br>old_name:it: Nuova York<br>place: city<br>population: 8467513<br>population:date: 2021-07-01<br>ref:us:ny:swis: 650000<br>short_name: NYC<br>source:name:oc: Lo Congrès<br>source:population: https://www.census.gov/quickfacts/newyorkcitynewyork<br>type: boundary<br>website: https://www.nyc.gov<br>wikidata: Q60<br>wikimedia_commons: Category:New York City<br>wikipedia: en:New York City"
                            },
                        }
                    ],
                },
            ),
        ),
        (
            "dist@1 query@2 around@4 center@1 nwr@1 keyval@2 name@0 Aston€Design@s search@1 nwr@1 keyval@2 amenity@0 library@s maxdist@1 DIST_INTOWN@0 topx@1 1@0 qtype@1 latlong@0",
            {
                "sub": [
                    {
                        "center_nwr": [("node", 6173229609)],
                        "target_nwr": (("amenity", "library"),),
                        "maxdist": Symbol("DIST_INTOWN"),
                        "around_topx": Symbol("1"),
                        "query_type": "around_query",
                        "qtype": (Symbol("latlong"),),
                    },
                ],
                "query_type": "dist",
            },
            MultiAnswer(answers=[DistAnswer(type='dist', dist=0.08982173981564252, target=(591360686, 'Newport Pagnell Library'), center=(6173229609, 'Aston Design'))], targets={'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-0.720658, 52.0862578]}, 'properties': {'popupContent': '<b>Newport Pagnell Library</b><br>lat: None lon: None<br>amenity: library<br>building: yes<br>name: Newport Pagnell Library<br>wikidata: Q55183712'}}]}, centers={'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-0.7219648, 52.0863175]}, 'properties': {'popupContent': '<b>Aston Design</b><br>lat: 52.0863175 lon: -0.7219648<br>name: Aston Design<br>shop: kitchen'}}]})
        )
    ],
)
def test_most_common_processor_chain(
    nominatim_and_overpass_cache, lin, expected_features_after_nwr_name_lookup, expected_multi_answer
):
    process_tool = ProcessingTool(PROCESSORS)
    request = ProcessingRequest(
        given={"Will2021Lin": lin},
        wanted={"Will2021FeaturesAfterNwrNameLookup", "Will2021MultiAnswer"},
        processors=set(),
    )
    expected_results = {
        "Will2021FeaturesAfterNwrNameLookup": expected_features_after_nwr_name_lookup,
        "Will2021MultiAnswer": expected_multi_answer,
    }
    result = process_tool.process_request(request)
    result = process_tool.select_wanted_from_result(result, request)
    assert result.results.keys() == expected_results.keys()
    assert all(expected_results[target] == single_result.result for target, single_result in result.results.items())
    assert all(isinstance(single_result.wallclock_seconds, float) for single_result in result.results.values())
    assert result.wallclock_seconds > sum(
        single_result.wallclock_seconds for single_result in result.results.values()
    )
