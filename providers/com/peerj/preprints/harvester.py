from providers.com.peerj.xml.harvester import PeerJXMLHarvester


class PeerJPreprintHarvester(PeerJXMLHarvester):
    base_url = 'https://peerj.com/preprints/index.json'
