require 'json'

module Jekyll
  class ForestPageGenerator < Generator
    safe true
    priority :normal

    def generate(site)
      forests = load_json(site, '_rawdata/forests.json')
      healings = load_json(site, '_rawdata/healing.json')
      arboretums = load_json(site, '_rawdata/arboretum.json')
      kidforests = load_json(site, '_rawdata/kidforest.json')

      Jekyll.logger.info "ForestGenerator:", "#{forests.size}개 휴양림 페이지 생성 중..."
      forests.each do |f|
        next if f['slug'].to_s.strip.empty?
        site.pages << ForestPage.new(site, f)
      end

      Jekyll.logger.info "ForestGenerator:", "#{healings.size}개 치유의숲 페이지 생성 중..."
      healings.each do |h|
        next if h['slug'].to_s.strip.empty?
        site.pages << HealingPage.new(site, h)
      end

      Jekyll.logger.info "ForestGenerator:", "#{arboretums.size}개 수목원 페이지 생성 중..."
      arboretums.each do |a|
        next if a['slug'].to_s.strip.empty?
        site.pages << ArboretumPage.new(site, a)
      end

      Jekyll.logger.info "ForestGenerator:", "#{kidforests.size}개 유아숲체험원 페이지 생성 중..."
      kidforests.each do |k|
        next if k['slug'].to_s.strip.empty?
        site.pages << KidForestPage.new(site, k)
      end

      site.pages << SearchIndexPage.new(site, forests, healings, arboretums, kidforests)

      Jekyll.logger.info "ForestGenerator:", "완료 (휴양림 #{forests.size}개 + 치유의숲 #{healings.size}개 + 수목원 #{arboretums.size}개 + 유아숲체험원 #{kidforests.size}개)"
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

  class HealingPage < Page
    def initialize(site, h)
      @site = site
      @base = site.source
      @dir  = "healing/#{h['slug']}"
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'healing.html')
      self.data.merge!(h)
      self.data['layout']      = 'healing'
      self.data['title']       = build_title(h)
      self.data['description'] = build_desc(h)
    end

    private

    def build_title(h)
      name = h['healingNm'] || ''
      loc  = [h['doShort'], h['sigungu']].compact.join(' ')
      "#{name} #{loc} 위치 프로그램 정보"
    end

    def build_desc(h)
      name = h['healingNm'] || ''
      loc  = [h['doShort'], h['sigungu']].compact.join(' ')
      type = h['manageType'] || ''
      "#{loc} #{name}(#{type}) 위치, 연락처, 참여방법을 확인하세요."[0, 155]
    end
  end

  class ArboretumPage < Page
    def initialize(site, a)
      @site = site
      @base = site.source
      @dir  = "arboretum/#{a['slug']}"
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'arboretum.html')
      self.data.merge!(a)
      self.data['layout']      = 'arboretum'
      self.data['title']       = build_title(a)
      self.data['description'] = build_desc(a)
    end

    private

    def build_title(a)
      name = a['arbName'] || ''
      loc  = [a['doShort'], a['sigungu']].compact.join(' ')
      "#{name} #{loc} 위치 이용시간 정보"
    end

    def build_desc(a)
      name = a['arbName'] || ''
      loc  = [a['doShort'], a['sigungu']].compact.join(' ')
      "#{loc} #{name} 위치, 이용시간, 주차, 휴무일을 확인하세요."[0, 155]
    end
  end

  class KidForestPage < Page
    def initialize(site, k)
      @site = site
      @base = site.source
      @dir  = "kidforest/#{k['slug']}"
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'kidforest.html')
      self.data.merge!(k)
      self.data['layout']      = 'kidforest'
      self.data['title']       = build_title(k)
      self.data['description'] = build_desc(k)
    end

    private

    def build_title(k)
      name = k['kfName'] || ''
      loc  = [k['doShort'], k['sigungu']].compact.join(' ')
      "#{name} #{loc} 위치 운영기간 참여방법"
    end

    def build_desc(k)
      intro = k['introText'].to_s
      return intro[0, 155] unless intro.empty?
      name = k['kfName'] || ''
      loc  = [k['doShort'], k['sigungu']].compact.join(' ')
      "#{loc} #{name} 위치, 운영기간, 참여방법을 확인하세요."[0, 155]
    end
  end

  class SearchIndexPage < Page
    def initialize(site, forests, healings, arboretums = [], kidforests = [])
      @site = site
      @base = site.source
      @dir  = ''
      @name = 'search_index.json'

      self.process(@name)
      self.data = { 'layout' => nil, 'sitemap' => false }

      forest_index = forests.map do |f|
        {
          'kind'         => 'forest',
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

      healing_index = healings.map do |h|
        {
          'kind'        => 'healing',
          'slug'        => h['slug'],
          'healingNm'   => h['healingNm'],
          'manageType'  => h['manageType'],
          'doShort'     => h['doShort'],
          'sigungu'     => h['sigungu'],
          'address'     => h['address'],
          'latitude'    => h['latitude'],
          'longitude'   => h['longitude'],
        }
      end

      arboretum_index = arboretums.map do |a|
        {
          'kind'      => 'arboretum',
          'slug'      => a['slug'],
          'arbName'   => a['arbName'],
          'doShort'   => a['doShort'],
          'sigungu'   => a['sigungu'],
          'address'   => a['address'],
          'image'     => a['image'],
          'latitude'  => a['latitude'],
          'longitude' => a['longitude'],
        }
      end

      kidforest_index = kidforests.map do |k|
        {
          'kind'        => 'kidforest',
          'slug'        => k['slug'],
          'kfName'      => k['kfName'],
          'doShort'     => k['doShort'],
          'sigungu'     => k['sigungu'],
          'address'     => k['address'],
          'phone'       => k['phone'],
          'operPeriod'  => k['operPeriod'],
          'participWay' => k['participWay'],
          'latitude'    => k['latitude'],
          'longitude'   => k['longitude'],
        }
      end

      self.content = (forest_index + healing_index + arboretum_index + kidforest_index).to_json
    end

    def output   = self.content
    def render(layouts, registers); end
  end
end
