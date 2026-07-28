require 'json'

module Jekyll
  class ForestPageGenerator < Generator
    safe true
    priority :normal

    def generate(site)
      forests = load_json(site, '_rawdata/forests.json')
      return if forests.empty?

      Jekyll.logger.info "ForestGenerator:", "#{forests.size}개 휴양림 페이지 생성 중..."

      forests.each do |f|
        next if f['slug'].to_s.strip.empty?
        site.pages << ForestPage.new(site, f)
      end

      site.pages << SearchIndexPage.new(site, forests)

      Jekyll.logger.info "ForestGenerator:", "완료 (#{forests.size}개)"
    end

    private

    def load_json(site, path)
      file = File.join(site.source, path)
      return [] unless File.exist?(file)
      JSON.parse(File.read(file, encoding: 'utf-8'))
    rescue => e
      Jekyll.logger.warn "ForestGenerator:", "#{path} 로드 실패: #{e.message}"
      []
    end
  end

  class ForestPage < Page
    def initialize(site, f)
      @site = site
      @base = site.source
      @dir  = "forest/#{f['slug']}"
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'forest.html')
      self.data.merge!(f)
      self.data['layout']      = 'forest'
      self.data['title']       = build_title(f)
      self.data['description'] = build_desc(f)
    end

    private

    def build_title(f)
      name = f['rcrfrstNm'] || ''
      loc  = [f['doShort'], f['sigungu']].compact.join(' ')
      "#{name} #{loc} 위치 요금 시설 정보"
    end

    def build_desc(f)
      name = f['rcrfrstNm'] || ''
      loc  = [f['doShort'], f['sigungu']].compact.join(' ')
      type = f['rcrfrstType'] || ''
      "#{loc} #{name}(#{type}) 위치, 이용요금, 시설, 숙박 가능 여부를 확인하세요."[0, 155]
    end
  end

  class SearchIndexPage < Page
    def initialize(site, forests)
      @site = site
      @base = site.source
      @dir  = ''
      @name = 'search_index.json'

      self.process(@name)
      self.data = { 'layout' => nil, 'sitemap' => false }

      index = forests.map do |f|
        {
          'slug'         => f['slug'],
          'rcrfrstNm'    => f['rcrfrstNm'],
          'rcrfrstType'  => f['rcrfrstType'],
          'doShort'      => f['doShort'],
          'sigungu'      => f['sigungu'],
          'rdnmadr'      => f['rdnmadr'],
          'stayngPosblYn'=> f['stayngPosblYn'],
          'latitude'     => f['latitude'],
          'longitude'    => f['longitude'],
        }
      end

      self.content = index.to_json
    end

    def output   = self.content
    def render(layouts, registers); end
  end
end
