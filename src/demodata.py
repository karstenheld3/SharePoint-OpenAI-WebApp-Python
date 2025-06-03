"""
Module containing demo data and crawler settings for the SharePoint Search application.
"""

# Demo responses for the query endpoint
DEMO_RESPONSES = [
  {
    "query": "lorem ipsum",
    "answer": "Lorem ipsum dolor sit amet【https://www.lipsum.com/feed/html】. Sed pharetra, augue ac sollicitudin hendrerit 【https://www.lipsum.com/feed/html】. Nullam in bibendum nibh 【https://www.lipsum.com/feed/html】.",
    "source_markers": ["【", "】"],
    "sources": [
      {
        "data": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam semper, lectus ullamcorper sagittis fermentum, nisi risus luctus ante, quis porttitor magna massa id diam. Sed magna orci, sagittis ut urna facilisis, vehicula sollicitudin justo. Mauris a vulputate leo. Nulla vehicula ultrices nisl eu gravida. Vestibulum purus diam, aliquet id est vel, ultrices ornare mauris. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Donec rutrum finibus elit ac tristique. Mauris molestie eros leo, vitae elementum est congue cursus. Suspendisse eu vehicula quam, eget faucibus nisl. Morbi et accumsan nunc. Fusce ut metus nec diam congue mattis ut eu dolor. Curabitur lacinia laoreet tellus ac suscipit. Curabitur euismod velit sit amet diam semper tincidunt.",
        "source": "https://www.lipsum.com/feed/html",
        "metadata": {"page": 1}
      },
      {
        "data": "Sed pharetra, augue ac sollicitudin hendrerit, nibh nulla interdum ligula, vitae maximus eros nulla id leo. Etiam at ligula turpis. Aenean convallis facilisis ligula, vitae ullamcorper sapien consequat ac. Vivamus ut eros venenatis, ultrices nunc id, pretium ex. Suspendisse id congue urna, nec blandit lectus. Nullam malesuada maximus varius. Quisque arcu est, ultricies quis sem id, hendrerit lacinia magna.",
        "source": "https://www.lipsum.com/feed/html",
        "metadata": {"page": 2}
      },
      {
        "data": "Nullam in bibendum nibh. Cras lobortis, nisi non scelerisque eleifend, lorem mauris rhoncus sapien, quis cursus elit eros nec libero. Pellentesque quis erat porta, consequat urna sagittis, posuere ipsum. Aliquam erat volutpat. Proin eget tellus nec elit iaculis lacinia. Ut et est congue, malesuada elit et, eleifend arcu. Duis dignissim condimentum tempus. Quisque tincidunt, quam ac elementum vulputate, quam elit vehicula metus, quis bibendum arcu nisl luctus mauris. Pellentesque sit amet eros vitae eros dignissim aliquam. Phasellus non felis purus. Donec odio odio, lacinia ac leo et, faucibus tempor quam. Mauris vulputate lacus nisl, vel tempor lacus sodales sit amet. Praesent consequat ultrices augue. Integer tristique turpis in vestibulum feugiat. Sed scelerisque non enim vel porttitor.",
        "source": "https://www.lipsum.com/feed/html",
        "metadata": {"page": 3}
      }
    ]
  }
]

# Crawler settings
CRAWLER_SETTINGS = {
  "domains": [
    {
      "key": "SharePoint-Demo-Site",
      "name": "SharePoint Demo Site",
      "description": "The default demo site.",
      "sources": [
        {
          "siteUrl": "",
          "documentLibraryUrlName": "Published",
          "documentFilter": ""
        }
      ]
    }
  ]
}
